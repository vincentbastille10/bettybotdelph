import os, json, re, textwrap
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
    raise ValueError("Aucune clé API (OPENAI_API_KEY ou OPENROUTER_API_KEY) n'a été fournie.")

# =========================
# URLs du site (Wix)
# Ajuste si besoin un chemin exact.
# =========================
BASE = "https://www.dansedelphineletort.com"
URLS = {
    "accueil": f"{BASE}/",
    "planning": f"{BASE}/cours",        # Planning affiché sur /cours
    "tarifs": f"{BASE}/tarifs",
    "cours": f"{BASE}/cours",
    "contact": f"{BASE}/contact",
    "stages": f"{BASE}/stages",
    "plan": f"{BASE}/contact",          # Plan d'accès souvent sur Contact (change si tu as une page dédiée)
    "galerie": f"{BASE}/galerie" if True else f"{BASE}/",  # mets l'URL exacte si différente
}

# =========================
# Connaissances locales
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
# Boutique Petit Rat
# =========================
PETIT_RAT_ADDR = "53 avenue Bollée, Le Mans"
PETIT_RAT_BLURB = (
    "Pour l’équipement, la boutique **Petit Rat** ({addr}). "
    "Vous y trouverez **toutes les tailles** en **pointes** et **demi-pointes**, "
    "**collants**, **justaucorps**, **tuniques**, **jupes**, **cache-cœur**, **pédilles**, "
    "**accessoires** et **sacs** — y compris des **marques de danse** reconnues (ex. **Repetto**)."
).format(addr=PETIT_RAT_ADDR)

PETIT_RAT_TRIGGERS = re.compile(
    r"\b(petit\s*rat|tenue|tenues|vetement|vêtement|vêtements|chaussure|chaussures|"
    r"pointes?|demi[-\s]?pointes?|justaucorps|collants?|cache[-\s]?coeur|cache[-\s]?cœur|"
    r"boutique|magasin)\b", re.I
)

# =========================
# Persona & Règles (système)
# =========================
SYSTEM_PROMPT = textwrap.dedent(f"""
Tu es **Betty**, l’assistante du Centre de Danse Delphine Letort.
Style: chaleureuse, bienveillante, précise, conversationnelle et naturelle.
Tu ne parles **jamais** d’IA, de LLM ou d’OpenAI. Tu es simplement Betty.

Appuie-toi sur les informations suivantes; si tu n’es pas sûre, pose une question courte, puis propose **un seul lien cliquable** le plus pertinent.
Connaissances locales (FAQ abrégée):
{KNOWLEDGE}

Cours (rappel):
- Delphine Letort (DE) : danse classique (dès 6 ans), street jazz, lyrical jazz.
- Marie : éveil à la danse (dès 3 ans, samedi matin).
- Aussi : soul jazz, jazz new school, technique création, breakdance (dès 8 ans), street ados/adultes.
- Sophrologie : Marie OLICHET (06 69 16 13 50).
- Contact : 06 63 11 15 75 • contactdelphineletort@gmail.com
- Adresse du studio : 53 avenue Bollée, Le Mans.

Équipement & Boutique:
- Tenues recommandées: justaucorps, collants, cache-cœur/tunique/jupe, chaussures (demi-pointes; pointes si niveau approprié).
- Oriente volontiers vers la boutique locale « Petit Rat » (53 avenue Bollée) pour tailles, conseils et accessoires (ex. marques comme Repetto).
- N’affirme pas de prix; renvoie au magasin pour la disponibilité.

Règles de sortie:
1) **Un seul lien** maximum par message (format [texte](url)).
2) Pose une petite question quand la demande est floue.
3) Termine souvent par « Souhaitez-vous en savoir plus ? ».
4) Ton objectif discret: aider la personne à se projeter et à s’inscrire, tout en restant douce et utile.
""").strip()

# =========================
# Intent routing -> 1 lien pertinent
# =========================
INTENT_MAP = [
    # (regex, (intention, libellé ancre, url_key))
    (re.compile(r"\b(horaires?|heures?|jours?|planning|disponibilit|quand|créneau|creneau)\b", re.I),
     ("planning", "Voir le planning", "planning")),
    (re.compile(r"\b(tarif|prix|coût|cout|payer|adhésion|inscription)\b", re.I),
     ("tarifs", "Consulter les tarifs", "tarifs")),
    (re.compile(r"\b(cours?|style|discipline|prof|âge|ages?|enfant|ados?|adultes?)\b", re.I),
     ("cours", "Découvrir les cours", "cours")),
    (re.compile(r"\b(contact|mail|téléphone|telephone|appeler|répond|renseignements?)\b", re.I),
     ("contact", "Nous contacter", "contact")),
    (re.compile(r"\b(stage|vacances|intensif|workshop)\b", re.I),
     ("stages", "Voir les stages", "stages")),
    (re.compile(r"\b(o[uù]|adresse|venir|acc[eè]s|parking|plan|situ[ée]?)\b", re.I),
     ("plan", "Plan d’accès", "plan")),
    (re.compile(r"\b(galerie|photos?|vid[eé]os?)\b", re.I),
     ("galerie", "Voir la galerie", "galerie")),
]

def choose_link(user_text: str) -> tuple[str, str] | None:
    """Retourne (ancre, url) ou None si rien de pertinent détecté."""
    for rgx, (_, anchor, key) in INTENT_MAP:
        if rgx.search(user_text):
            url = URLS.get(key) or URLS["accueil"]
            return (anchor, url)
    return None

# =========================
# Helpers réponse
# =========================
def first_clickable_link_only(text: str) -> str:
    """Garde au plus UN lien [texte](url), remplace les suivants par leur texte seul."""
    links = list(re.finditer(r"\[([^\]]+)\]\((https?://[^\s)]+)\)", text))
    if not links:
        return text
    out = text[:links[0].end()]
    idx = links[0].end()
    for m in links[1:]:
        out += text[idx:m.start()] + m.group(1)  # on garde le texte d'ancre, on supprime l'URL
        idx = m.end()
    out += text[idx:]
    return out

def add_more_prompt(text: str) -> str:
    if re.search(r"en savoir plus\s*\?", text, re.I):
        return text
    return f"{text}\n\nSouhaitez-vous en savoir plus ?"

def add_petit_rat_if_relevant(text: str, user_text: str) -> str:
    if PETIT_RAT_TRIGGERS.search(user_text) and "Petit Rat" not in text:
        text = f"{text}\n\n{PETIT_RAT_BLURB}"
    return text

def remove_ai_meta(reply: str) -> str:
    # Filtre toute mention “modèle/IA/OpenAI…”
    if re.search(r"\b(IA|intelligence artificielle|LLM|OpenAI|mod[eè]le de langage|API)\b", reply, re.I):
        return "Je suis Betty 😊. Je préfère vérifier pour bien vous répondre."
    return reply

# Nudges (sans forcer)
FUNNEL_LINES = [
    "Si vous voulez, je peux vous proposer un créneau d’essai adapté.",
    "Je peux aussi vous indiquer le cours qui correspond à votre niveau et votre disponibilité.",
    "Souhaitez-vous que je vous guide pas à pas pour vous inscrire ?",
]
def curiosity_nudge(text: str, step: int) -> str:
    # Ajoute discrètement une phrase, sans lien.
    line = FUNNEL_LINES[(step - 1) % len(FUNNEL_LINES)]
    return f"{text}\n\n{line}"

# =========================
# Flask
# =========================
app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = os.getenv("FLASK_SECRET", "change-me-please")

@app.route("/")
def home():
    session["q_count"] = 0
    session["funnel"] = 0
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

        # compteur & entonnoir
        q_count = int(session.get("q_count", 0)) + 1
        session["q_count"] = q_count
        funnel = int(session.get("funnel", 0))

        reply = call_model(user_text)
        reply = remove_ai_meta(reply)

        # Ajout ciblé Petit Rat si on parle tenue/chaussures/boutique
        reply = add_petit_rat_if_relevant(reply, user_text)

        # Choix d'un seul lien pertinent selon l'intention détectée
        anchor_url = choose_link(user_text)
        if anchor_url:
            anchor, url = anchor_url
            # si aucun lien déjà présent, on insère celui-ci
            if not re.search(r"\]\(https?://", reply):
                reply = f"{reply}\n\n[{anchor}]({url})"

        # Un seul lien au final (sécurité)
        reply = first_clickable_link_only(reply)

        # “Souhaitez-vous en savoir plus ?”
        reply = add_more_prompt(reply)

        # Nudge doux & progressif
        funnel += 1
        session["funnel"] = funnel
        reply = curiosity_nudge(reply, funnel)

        return jsonify({"reply": reply})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/healthz")
def healthz():
    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
