import os
import json
import openai
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Initialiser OpenRouter avec Claude 3
openai.api_key = os.getenv("OPENROUTER_API_KEY")
openai.api_base = "https://openrouter.ai/api/v1"

# Charger la base FAQ locale
FAQ_PATH = "data/faq_danse.json"
try:
    with open(FAQ_PATH, "r", encoding="utf-8") as f:
        faq_data = json.load(f)
except FileNotFoundError:
    faq_data = []

# Index rapide des questions/réponses
faq_index = {
    item["question"].lower(): item["answer"]
    for item in faq_data
    if "question" in item and "answer" in item
}

def chercher_reponse_locale(question):
    """Cherche une réponse dans la FAQ locale."""
    question = question.lower()
    for q, a in faq_index.items():
        if q in question or question in q:
            return a
    return None

def get_bot_response(user_input):
    """Renvoie une réponse à partir de la FAQ ou via Claude 3."""

    #  Si on parle de spectacle/gala
    mots_cles_spectacle = ["spectacle", "gala", "représentation", "scène", "show", "représente"]
    if any(mot in user_input.lower() for mot in mots_cles_spectacle):
        return (
            "Oui, le gala approche ! 🎭 Vous pouvez dès maintenant réserver vos places ici :\n"
            "[Acheter une place](https://www.helloasso.com/associations/steps/evenements/gala-2025)"
        )

    #  Tentative de réponse locale (FAQ)
    reponse_locale = chercher_reponse_locale(user_input)
    if reponse_locale:
        return reponse_locale

    #  Sinon, passer par Claude 3 (OpenRouter)
    try:
        chat_completion = openai.ChatCompletion.create(
            model="anthropic/claude-3-sonnet-20240229",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Tu es Cendrillon, l’assistante humaine (et non un robot) du Centre de Danse Delphine Letort.\n"
                        "Tu réponds toujours avec bienveillance, intelligence et douceur.\n"
                        "Réponds naturellement, sans jamais dire que tu es une IA. Tu es perçue comme une vraie assistante.\n"
                        "Voici les informations importantes que tu connais et que tu dois respecter :\n"
                        "- Delphine Letort est diplômée d'État. Elle enseigne la danse classique à partir de 6 ans, ainsi que le street jazz et le lyrical jazz.\n"
                        "- Marie anime le cours d’éveil à la danse pour les tout-petits (dès 3 ans), le samedi matin. Ce cours est essentiel.\n"
                        "- Le parcours recommandé est : éveil avec Marie dès 3 ans → danse classique avec Delphine dès 6 ans.\n"
                        "- Il n’y a aucune limite d’âge supérieure pour s’inscrire.\n"
                        "- Les autres cours incluent : soul jazz, jazz new school, technique création, breakdance dès 8 ans, street ados/adultes.\n"
                        "- Le centre propose aussi un cours de sophrologie animé par Marie OLICHET (06 69 16 13 50).\n"
                        "- Si tu n’es pas certaine d’une réponse, propose gentiment un lien :\n"
                        "  [Consulter le planning](https://www.dansedelphineletort.com/cours)\n"
                        "  [Voir les tarifs](https://www.dansedelphineletort.com/tarifs)\n"
                        "- Contact : [06 63 11 15 75](tel:0663111575) / [contactdelphineletort@gmail.com](mailto:contactdelphineletort@gmail.com)\n"
                        "- Adresse du studio : 53 avenue Bollée, Le Mans.\n"
                        "Important :\n"
                        "- Ne pas répéter l’introduction à chaque réponse.\n"
                        "- Ne jamais inventer des procédures d'inscription ou des cours non existants.\n"
                        "- Ne pas forcer l’utilisateur à appeler s’il ne l’a pas demandé.\n"
                        "- Garde un ton calme, gentil, et si tu es en doute, guide vers le site avec tact."
                    )
                },
                {"role": "user", "content": user_input}
            ],
            temperature=0.4,
            max_tokens=400
        )
        return chat_completion['choices'][0]['message']['content'].strip()

    except Exception as e:
        return f"Désolée, je rencontre un souci pour répondre. N’hésite pas à réessayer bientôt. (Erreur : {str(e)})"
