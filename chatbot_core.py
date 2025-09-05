# chatbot_core.py
import os
import glob
import json
from datetime import date
from typing import List, Dict

import openai
from dotenv import load_dotenv

# ----------------------------------------------------------------------
# ENV & OpenAI (API v0.28)
# ----------------------------------------------------------------------
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
MODEL_ID = os.getenv("MODEL_ID", "gpt-3.5-turbo")

# ----------------------------------------------------------------------
# FAQ LOCALE
# ----------------------------------------------------------------------
FAQ_PATH = "data/faq_danse.json"
try:
    with open(FAQ_PATH, "r", encoding="utf-8") as f:
        faq_data = json.load(f)
except Exception:
    faq_data = []

faq_index = {
    str(item.get("question", "")).lower(): item.get("answer", "")
    for item in faq_data
    if isinstance(item, dict)
}

def chercher_reponse_locale(question: str):
    """Cherche une réponse dans la FAQ locale (matching simple)."""
    q = (question or "").lower()
    for k, v in faq_index.items():
        if k and (k in q or q in k):
            return v
    return None

# ----------------------------------------------------------------------
# BASE DE CONNAISSANCES (fichiers .md / .txt)
# ----------------------------------------------------------------------
def _read_text_file(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception:
        return ""

def load_kb_texts() -> List[Dict[str, str]]:
    """Charge les textes depuis data/ et personnalisées/ (md/txt)."""
    texts = []
    for folder in ["data", "personnalisées"]:
        if not os.path.isdir(folder):
            continue
        for p in glob.glob(os.path.join(folder, "**", "*.*"), recursive=True):
            if p.lower().endswith((".md", ".txt")):
                txt = _read_text_file(p)
                if txt.strip():
                    texts.append({"source": p, "text": txt})
    return texts

KB_DOCS = load_kb_texts()

def extract_offer_snippet(kb_docs: List[Dict[str, str]]) -> str:
    """Essaie d'extraire la section OFFRE SEPTEMBRE dans les .md si présente."""
    keys = ["offre septembre", "cours d’essai", "cours d'essai", "essai gratuit"]
    for doc in kb_docs:
        low = doc["text"].lower()
        if any(k in low for k in keys):
            snippet = doc["text"]
            for marker in ["## OFFRE SEPTEMBRE", "OFFRE SEPTEMBRE", "Offre — Cours d’essai", "Offre - Cours d’essai"]:
                idx = snippet.find(marker)
                if idx != -1:
                    snippet = snippet[idx:]
                    break
            return snippet[:900]
    return ""

OFFER_SNIPPET = extract_offer_snippet(KB_DOCS)

def build_small_context(kb_docs: List[Dict[str, str]], limit_chars: int = 1200) -> str:
    """Construit un petit contexte concaténé et safe (~1200 chars)."""
    parts = []
    total = 0
    preferred_first = sorted(
        kb_docs,
        key=lambda d: 0 if "reglement+offre" in d["source"].lower() else 1
    )
    for d in preferred_first:
        txt = d["text"].strip()
        if not txt:
            continue
        remain = limit_chars - total
        if remain <= 0:
            break
        chunk = txt[:remain]
        parts.append(f"[{os.path.basename(d['source'])}]\n{chunk}")
        total += len(chunk)
    return "\n\n".join(parts)

SMALL_CONTEXT = build_small_context(KB_DOCS)

# ----------------------------------------------------------------------
# RÈGLE MÉTIER : PROMO SEPTEMBRE
# ----------------------------------------------------------------------
def promo_septembre_active() -> bool:
    return date.today().month == 9

PROMO_MSG = (
    "**En septembre : 1 cours d’essai gratuit** par personne (places limitées). "
    "Réservation obligatoire via le lien *Inscription* du site ou WhatsApp. "
    "L’essai n’engage pas ; si vous poursuivez, le règlement intérieur s’applique."
)

def wants_offer(user_msg: str) -> bool:
    """Détection large des intentions essai/offre/gratuit."""
    msg = (user_msg or "").lower()
    return any(k in msg for k in [
        # essai / offre / période
        "essai", "essayer", "offre", "septembre", "test", "découvrir",
        "essayer un cours", "essai gratuit", "cours d'essai", "cours d’essai",
        # gratuit
        "gratuit", "gratuite", "free"
    ])

def must_attach_offer(msg_user: str, draft_answer: str) -> bool:
    """Faut-il ajouter la promo à la réponse ?"""
    if not promo_septembre_active():
        return False
    if PROMO_MSG in (draft_answer or ""):
        return False
    msg = (msg_user or "").lower()
    return any(k in msg for k in [
        "prix","tarif","inscription","essai","septembre","offre","cours","test",
        "gratuit","gratuite","free"
    ])

# ----------------------------------------------------------------------
# RÉPONSE BOT
# ----------------------------------------------------------------------
def get_bot_response(user_input: str) -> str:
    """Renvoie une réponse depuis la FAQ, sinon via OpenAI, avec règles métier."""

    # 0) Règle rapide : spectacle/gala
    mots_cles_spectacle = ["spectacle", "gala", "représentation", "scène", "show", "représente"]
    if any(mot in (user_input or "").lower() for mot in mots_cles_spectacle):
        return (
            "Oui, le gala approche ! 🎭 Vous pouvez dès maintenant réserver vos places ici :\n"
            "[Acheter une place](https://www.helloasso.com/associations/steps/evenements/gala-2025)"
        )

    # 1) Promo septembre — réponse proactive si pertinent
    proactive_offer = ""
    if promo_septembre_active() and wants_offer(user_input):
        details = OFFER_SNIPPET or (
            "Du 1er au 30 septembre : 1 cours d’essai gratuit par personne, sur le cours de votre choix "
            "(dans la limite des places). Réservation obligatoire en ligne/WhatsApp. "
            "Venez 10 minutes en avance avec une tenue adaptée."
        )
        proactive_offer = f"{PROMO_MSG}\n\n{details}"

    # 2) FAQ locale si pas de proactive_offer
    if not proactive_offer:
        local = chercher_reponse_locale(user_input)
        if local:
            if promo_septembre_active() and must_attach_offer(user_input, local):
                local += "\n\n" + PROMO_MSG
            return local

    # 3) OpenAI (contexte court + promo en consigne)
    try:
        system_msg = (
            "Tu es Cendrillon, l’assistante humaine (et non un robot) du Centre de Danse Delphine Letort. "
            "Tu réponds avec bienveillance, clarté et douceur. Ne mentionne jamais que tu es une IA.\n"
            "Infos clés :\n"
            "- Delphine Letort (diplômée d'État) enseigne classique (dès 6 ans), street jazz et lyrical jazz.\n"
            "- Marie anime l’éveil à la danse (dès 3 ans) le samedi matin.\n"
            "- Parcours recommandé : éveil (dès 3 ans) → classique (dès 6 ans).\n"
            "- Aucune limite d’âge supérieure pour s’inscrire.\n"
            "- Autres cours : soul jazz, jazz new school, technique création, breakdance dès 8 ans, street ados/adultes.\n"
            "- Sophrologie : Marie OLICHET (06 69 16 13 50).\n"
            "- Liens utiles : planning https://www.dansedelphineletort.com/cours ; "
            "tarifs https://www.dansedelphineletort.com/tarifs\n"
            "- Contact : 06 63 11 15 75 / contactdelphineletort@gmail.com ; "
            "Adresse : 53 avenue Bollée, Le Mans.\n"
            "Règles : ne pas répéter l’intro à chaque réponse ; ne pas inventer ; rester gentil et rediriger vers le site si doute.\n"
        )

        if promo_septembre_active():
            system_msg += (
                "\nIMPORTANT (période courante) : En septembre, proposer proactivement l’offre "
                "« 1 cours d’essai gratuit par personne ». Rappeler que la réservation est obligatoire "
                "via le lien Inscription (places limitées)."
            )

        context_block = ""
        if SMALL_CONTEXT:
            context_block = (
                "\n\nContexte (extraits internes, ne pas citer textuellement si inutile) :\n"
                + SMALL_CONTEXT
            )

        messages = [{"role": "system", "content": system_msg + context_block}]
        if proactive_offer:
            messages.append({"role": "system", "content": "Rappelle l'offre d'essai gratuite en septembre si pertinent."})
        messages.append({"role": "user", "content": user_input or ""})

        chat_completion = openai.ChatCompletion.create(
            model=MODEL_ID,
            messages=messages,
            temperature=0.4,
            max_tokens=550,
        )

        draft = chat_completion["choices"][0]["message"]["content"].strip()

        # 4) Post-traitement : garantir l'annonce de la promo si pertinent
        if promo_septembre_active() and wants_offer(user_input) and PROMO_MSG not in draft:
            draft = PROMO_MSG + "\n\n" + draft
        elif must_attach_offer(user_input, draft):
            draft += "\n\n" + PROMO_MSG

        if proactive_offer and proactive_offer not in draft:
            draft = proactive_offer + "\n\n" + draft

        return draft

    except Exception as e:
        return (
            "Désolée, je rencontre un souci pour répondre. N’hésite pas à réessayer bientôt. "
            f"(Erreur : {str(e)})"
        )
