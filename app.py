# app.py — Betty (typos + Petit Rat + bulle bleue)

import os, json, re, textwrap, unicodedata
import openai
from flask import Flask, request, jsonify, render_template, session
from dotenv import load_dotenv

# =========================
# ENV & Provider
# =========================
load_dotenv()
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL_ID = os.getenv("MODEL_ID", "openai/gpt-4o-mini")

if OPENAI_KEY:
    openai.api_key = OPENAI_KEY
    openai.api_base = "https://api.openai.com/v1"
elif OPENROUTER_KEY:
    openai.api_key = OPENROUTER_KEY
    openai.api_base = "https://openrouter.ai/api/v1"
else:
    raise ValueError("Aucune clé API (OPENAI_API_KEY ou OPENROUTER_API_KEY).")

# =========================
# URLs du site
# =========================
BASE = "https://www.dansedelphineletort.com"
URLS = {
    "accueil": f"{BASE}/",
    "planning": f"{BASE}/cours",
    "tarifs": f"{BASE}/tarifs",
    "cours": f"{BASE}/cours",
    "contact": f"{BASE}/contact",
    "stages": f"{BASE}/stages",
    "plan": f"{BASE}/contact",   # ajuste si page dédiée
    "galerie": f"{BASE}/galerie" if True else f"{BASE}/",
}

# =========================
# FAQ locale (facultatif)
# =========================
FAQ_PATH = os.getenv("FAQ_PATH", "data/faq_danse.json")
def load_faq():
    try:
        with open(FAQ_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        items = []
        for it in data:
            q = (it.get("question") or "").strip()
            a = (it.get("answer") or "").strip()
            if q and a:
                items.append(f"Q: {q}\nR: {a}")
        return "\n\n".join(items)[:4000]
    except Exception:
        return ""
KNOWLEDGE = load_faq()

# =========================
# Petit Rat
# =========================
PETIT_RAT_ADDR = "53 avenue Bollée, Le Mans"
PETIT_RAT_BLURB = (
    "Pour l’équipement, la boutique **Petit Rat** ({addr}). "
    "Vous y trouverez **toutes les tailles** en **pointes** et **demi-pointes**, "
    "**collants**, **justaucorps**, **tuniques**, **jupes**, **cache-cœur**, **pédilles**, "
    "**accessoires** et **sacs** — y compris des **marques de danse** reconnues (ex. **Repetto**)."
).format(addr=PETIT_RAT_ADDR)

# -------------------------
# Normalisation & Fuzzy
# -------------------------
def norm(s: str) -> str:
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    s = re.sub(r"(.)\1{2,}", r"\1\1", s)  # aaa -> aa
    return s.strip()

def trigrams(s: str) -> set:
    s = f"  {s}  "
    return {s[i:i+3] for i in range(len(s)-2)}

def similar(a: str, b: str) -> float:
    """Jaccard sur trigrammes (léger mais robuste aux typos)."""
    A, B = trigrams(a), trigrams(b)
    if not A or not B: return 0.0
    return len(A & B) / len(A | B)

def fuzzy_has(text: str, keywords: list[str], threshold: float = 0.45) -> bool:
    t = norm(text)
    words = t.split()
    for kw in keywords:
        k = norm(kw)
        if k in t:
            return True
        # check par mot
        for w in words:
            if similar(w, k) >= threshold:
                return True
        # check global
        if similar(t, k) >= threshold:
            return True
    return False

# Triggers tenues/chaussures/boutique (+ fautes courantes)
CLOTHES_TERMS = [
    "tenue", "tenues", "vetement", "vêtement", "vêtements", "habit", "habits", "habiys", "habiy",
    "chaussure", "chaussures", "pointes", "demi pointes", "demi-pointes", "demipointes",
    "justaucorps", "collants", "cache coeur", "cache-cœur", "cache coeur",
    "boutique", "magasin", "petit rat", "p tit rat", "ptit rat", "p'tit rat"
]

INSCRIPTION_TERMS = [
    "inscription", "s inscrire", "inscrire", "m inscrire", "je veux m inscrire",
    "ok", "d accord", "d’accord", "oui", "let s go", "go"
]

# =========================
# Persona (système)
# =========================
SYSTEM_PROMPT = textwrap.dedent(f"""
Tu es **Betty**, l’assistante du Centre de Danse Delphine Letort.
Style: chaleureuse, bienveillante, précise et naturelle. **Ne parle jamais d’IA/LLM/OpenAI**.

Infos utiles (résumé):
{KNOWLEDGE}

Cours:
- Delphine Letort (DE) : classique (dès 6 ans), street jazz, lyrical jazz.
- Marie : éveil (dès 3 ans, samedi matin).
- Aussi : soul jazz, jazz new school, technique création, breakdance (dès 8 ans), street ados/adultes.
- Sophrologie : Marie OLICHET (06 69 16 13 50).
- Contact : 06 63 11 15 75 • contactdelphineletort@gmail.com
- Studio : 53 avenue Bollée, Le Mans.

Équipement & Boutique:
- Tenues: justaucorps, collants, cache-cœur/tunique/jupe; chaussures: demi-pointes, pointes si niveau approprié.
- Oriente vers la boutique locale « Petit Rat » (53 avenue Bollée) pour tailles, conseils et accessoires (ex. Repetto).
- Ne donne pas de prix; renvoie au magasin.

Règles:
- **1 seul lien** cliquable par message (format [texte](url)).
- Si la demande est floue, pose une courte question.
- Termine souvent par « Souhaitez-vous en savoir plus ? ».
- Objectif discret: aider la personne à se projeter et à s’inscrire (ton doux, sans forcer).
""").strip()

# =========================
# Intent routing -> 1 lien
# =========================
INTENT_MAP = [
    (re.compile(r"\b(horaires?|heures?|jours?|planning|disponibilit|quand|créneau|creneau)\b", re.I),
     ("Voir le planning", "planning")),
    (re.compile(r"\b(tarif|prix|co[uû]t|payer|adh[ée]sion|inscription)\b", re.I),
     ("Consulter les tarifs", "tarifs")),
    (re.compile(r"\b(cours?|style|discipline|prof|âge|ages?|enfant|ados?|adultes?)\b", re.I),
     ("Découvrir les cours", "cours")),
    (re.compile(r"\b(contact|mail|t[ée]l[ée]phone|appeler|renseignement)\b", re.I),
     ("Nous contacter", "contact")),
    (re.compile(r"\b(stage|vacances|intensif|workshop)\b", re.I),
     ("Voir les stages", "stages")),
    (re.compile(r"\b(adresse|venir|acc[eè]s|parking|plan|situ[ée]?)\b", re.I),
     ("Plan d’accès", "plan")),
    (re.compile(r"\b(galerie|photos?|vid[ée]os?)\b", re.I),
     ("Voir la galerie", "galerie")),
]

def choose_link(user_text: str) -> tuple[str, str] | None:
    for rgx, (anchor, key) in INTENT_MAP:
        if rgx.search(user_text):
            return (anchor, URLS.get(key, URLS["accueil"]))
    return None

# =========================
# Helpers de sortie
# =========================
def first_clickable_link_only(text: str) -> str:
    links = list(re.finditer(r"\[([^\]]+)\]\((https?://[^\s)]+)\)", text))
    if not links:
        return text
    out = text[:links[0].end()]
    idx = links[0].end()
    for m in links[1:]:
        out += text[idx:m.start()] + m.group(1)
        idx = m.end()
    out += text[idx:]
    return out

def add_more_prompt(text: str) -> str:
    if re.search(r"en savoir plus\s*\?", text, re.I): return text
    return f"{text}\n\nSouhaitez-vous en savoir plus ?"

def add_petit_rat_if_relevant(text: str, user_text: str) -> str:
    if fuzzy_has(user_text, CLOTHES_TERMS) and "Petit Rat" not in text:
        text = f"{text}\n\n{PETIT_RAT_BLURB}"
    return text

def remove_ai_meta(reply: str) -> str:
    if re.search(r"\b(IA|intelligence artificielle|LLM|OpenAI|mod[eè]le de langage|API)\b", reply, re.I):
        return "Je suis Betty 😊. Je préfère vérifier pour bien vous répondre."
    return reply

WIX_BULLE = "💡 Pour vous inscrire rapidement, cliquez sur **la petite bulle bleue en bas à droite**."
def bulle_cta(text: str, user_text: str, force: bool = False) -> str:
    if force or fuzzy_has(user_text, INSCRIPTION_TERMS):
        if WIX_BULLE not in text:
            return f"{text}\n\n{WIX_BULLE}"
    return text

# =========================
# Flask
# =========================
app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = os.getenv("FLASK_SECRET", "change-me-please")

@app.route("/")
def home():
    session["q_count"] = 0
    return render_template("widget.html")

def extract_user_text(payload: dict) -> str:
    for k in ("message","text","content","prompt","msg","q","question"):
        v = payload.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""

def call_model(user_text: str) -> str:
    resp = openai.ChatCompletion.create(
        model=MODEL_ID,
        temperature=0.35,
        max_tokens=600,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_text},
        ],
    )
    return resp["choices"][0]["message"]["content"].strip()

@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json(force=True) or {}
        user_text = extract_user_text(data)
        if not user_text:
            return jsonify({"error":"Message manquant"}), 400

        # compteur questions → rappel bulle toutes les 2
        q = int(session.get("q_count", 0)) + 1
        session["q_count"] = q

        reply = call_model(user_text)
        reply = remove_ai_meta(reply)

        # 1) Petit Rat (détection floue, même avec fautes)
        reply = add_petit_rat_if_relevant(reply, user_text)

        # 2) Lien contextuel (1 seul max)
        anchor_url = choose_link(user_text)
        if anchor_url and not re.search(r"\]\(https?://", reply):
            anchor, url = anchor_url
            reply = f"{reply}\n\n[{anchor}]({url})"
        reply = first_clickable_link_only(reply)

        # 3) “En savoir plus ?”
        reply = add_more_prompt(reply)

        # 4) Inscription (bulle bleue Wix)
        #    - forcer si l’utilisateur écrit "inscription / s'inscrire / oui / ok / d'accord"
        reply = bulle_cta(reply, user_text, force=fuzzy_has(user_text, INSCRIPTION_TERMS))
        #    - rappel automatique toutes les 2 questions
        if q % 2 == 0:
            reply = bulle_cta(reply, user_text, force=True)

        return jsonify({"reply": reply})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/healthz")
def healthz():
    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
