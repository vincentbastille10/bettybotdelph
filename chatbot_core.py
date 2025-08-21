import os
import json
import openai
from dotenv import load_dotenv

# Charge les variables d'environnement (.env ou Render)
load_dotenv()

# --- CONFIG OPENAI (v0.28) ---
# Utilise ta clé OpenAI (PAS OpenRouter)
openai.api_key = os.getenv("OPENAI_API_KEY")

# Modèle pilotable par variable d'env, sinon défaut sûr en 0.28
MODEL_ID = os.getenv("MODEL_ID", "gpt-3.5-turbo")

# --- FAQ LOCALE ---
FAQ_PATH = "data/faq_danse.json"
try:
    with open(FAQ_PATH, "r", encoding="utf-8") as f:
        faq_data = json.load(f)
except FileNotFoundError:
    faq_data = []

faq_index = {
    item["question"].lower(): item["answer"]
    for item in faq_data
    if isinstance(item, dict) and "question" in item and "answer" in item
}

def chercher_reponse_locale(question: str):
    """Cherche une réponse dans la FAQ locale (matching simple)."""
    q = (question or "").lower()
    for k, v in faq_index.items():
        if k in q or q in k:
            return v
    return None

def get_bot_response(user_input: str) -> str:
    """Renvoie une réponse depuis la FAQ sinon via OpenAI (v0.28)."""

    # Règle rapide : spectacle/gala
    mots_cles_spectacle = ["spectacle", "gala", "représentation", "scène", "show", "représente"]
    if any(mot in (user_input or "").lower() for mot in mots_cles_spectacle):
        return (
            "Oui, le gala approche ! 🎭 Vous pouvez dès maintenant réserver vos places ici :\n"
            "[Acheter une place](https://www.helloasso.com/associations/steps/evenements/gala-2025)"
        )

    # 1) Tentative FAQ locale
    local = chercher_reponse_locale(user_input)
    if local:
        return local

    # 2) Appel modèle OpenAI (API ancienne 0.28)
    try:
        chat_completion = openai.ChatCompletion.create(
            model=MODEL_ID,  # ex: "gpt-3.5-turbo" ou "gpt-4"
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Tu es Cendrillon, l’assistante humaine (et non un robot) du Centre de Danse Delphine Letort. "
                        "Tu réponds avec bienveillance, clarté et douceur. Ne mentionne jamais que tu es une IA.\n"
                        "Infos clés :\n"
                        "- Delphine Letort (diplômée d'État) enseigne classique (dès 6 ans), street jazz et lyrical jazz.\n"
                        "- Marie anime l’éveil à la danse pour les tout-petits (dès 3 ans), le samedi matin.\n"
                        "- Parcours recommandé : éveil (dès 3 ans) → classique (dès 6 ans).\n"
                        "- Aucune limite d’âge supérieure pour s’inscrire.\n"
                        "- Autres cours : soul jazz, jazz new school, technique création, breakdance dès 8 ans, street ados/adultes.\n"
                        "- Sophrologie : Marie OLICHET (06 69 16 13 50).\n"
                        "- Liens utiles : planning https://www.dansedelphineletort.com/cours ; tarifs https://www.dansedelphineletort.com/tarifs\n"
                        "- Contact : 06 63 11 15 75 / contactdelphineletort@gmail.com ; Adresse : 53 avenue Bollée, Le Mans.\n"
                        "Règles : ne pas répéter l’intro à chaque réponse ; ne pas inventer ; rester gentil et rediriger vers le site si doute."
                    ),
                },
                {"role": "user", "content": user_input or ""},
            ],
            temperature=0.4,
            max_tokens=500,
        )

        return chat_completion["choices"][0]["message"]["content"].strip()

    except Exception as e:
        # Message d’erreur propre côté utilisateur
        return f"Désolée, je rencontre un souci pour répondre. N’hésite pas à réessayer bientôt. (Erreur : {str(e)})"
