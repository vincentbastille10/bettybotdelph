from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
from groq import Groq
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Initialisation de Flask
app = Flask(__name__)
CORS(app)

# Récupération de la clé API Groq
groq_api_key = os.getenv("GROQ_API_KEY")
if not groq_api_key:
    raise ValueError("GROQ_API_KEY est manquant dans les variables d'environnement.")

# Initialiser le client Groq
client = Groq(api_key=groq_api_key)

# Charger la base FAQ locale si disponible
FAQ_PATH = "data/faq_danse.json"
try:
    with open(FAQ_PATH, "r", encoding="utf-8") as f:
        faq_data = json.load(f)
except FileNotFoundError:
    faq_data = []

# Indexation pour recherche rapide
faq_index = {
    item["question"].lower(): item["answer"]
    for item in faq_data
    if "question" in item and "answer" in item
}

def chercher_reponse_locale(question):
    """Tente de répondre en local à partir de la FAQ"""
    question = question.lower()
    for q, a in faq_index.items():
        if q in question or question in q:
            return a
    return None

def get_bot_response(user_input):
    """Fournit une réponse, d'abord via la FAQ locale, sinon via Groq"""
    reponse_locale = chercher_reponse_locale(user_input)
    if reponse_locale:
        return reponse_locale

    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Tu es Betty, l’assistante humaine (et non un robot) du Centre de Danse Delphine Letort.\n"
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
            model="llama3-8b-8192",
            temperature=0.4
        )
        return chat_completion.choices[0].message.content

    except Exception as e:
        return f"Désolée, je rencontre un souci pour répondre. N’hésite pas à réessayer bientôt. (Erreur : {str(e)})"

@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json()
    user_input = data.get("message", "")
    if not user_input:
        return jsonify({"error": "Message vide"}), 400
    response = get_bot_response(user_input)
    return jsonify({"response": response})

# Point de départ de l’application
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Render définit PORT automatiquement
    app.run(host="0.0.0.0", port=port)
