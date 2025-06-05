import os
import json
from groq import Groq
from dotenv import load_dotenv

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()

# Récupérer la clé API GROQ
groq_api_key = os.getenv("GROQ_API_KEY")
if not groq_api_key:
    raise ValueError("GROQ_API_KEY est manquant dans les variables d'environnement.")

# Initialiser le client Groq
client = Groq(api_key=groq_api_key)

# Charger la base de connaissances locale
FAQ_PATH = "data/faq_danse.json"
try:
    with open(FAQ_PATH, "r", encoding="utf-8") as f:
        faq_data = json.load(f)
except FileNotFoundError:
    faq_data = []

# Indexer les données FAQ pour une recherche rapide
faq_index = {
    item["question"].lower(): item["answer"]
    for item in faq_data
    if "question" in item and "answer" in item
}

def chercher_reponse_locale(question):
    question = question.lower()
    for q, a in faq_index.items():
        if q in question or question in q:
            return a
    return None

def get_bot_response(user_input):
    reponse_locale = chercher_reponse_locale(user_input)
    if reponse_locale:
        return reponse_locale

    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Tu es Betty, l’assistante gentille du Centre de Danse Delphine Letort.\n"
                        "Tu réponds toujours avec chaleur, clarté et un petit sourire dans la voix.\n"
                        "Voici les informations à ta disposition :\n"
                        "- Delphine Letort est diplômée d'État. Elle enseigne la danse classique à partir de 6 ans, ainsi que le street jazz et le lyrical jazz.\n"
                        "- Marie enseigne l’éveil à la danse pour les enfants dès 3 ans, le samedi matin.\n"
                        "- Le classique est au cœur de l’enseignement : les enfants commencent dès 3 ans avec Marie, puis poursuivent avec Delphine.\n"
                        "- Aucune limite d’âge n’est imposée pour s’inscrire.\n"
                        "- Autres cours proposés : jazz new school, soul jazz, break-dance (dès 8 ans), Technique-Création (mardi 18h15), street adultes/ados (mercredi 20h45).\n"
                        "- Sophrologie : chaque vendredi avec Marie OLICHET (06 69 16 13 50).\n"
                        "- Planning : https://www.dansedelphineletort.com/cours\n"
                        "- Tarifs : https://www.dansedelphineletort.com/tarifs\n"
                        "- Contact : 06 63 11 15 75 / contactdelphineletort@gmail.com\n"
                        "- Adresse : 53 avenue Bollée, Le Mans.\n"
                        "Ne propose les liens que si tu ne connais pas la réponse exacte. Tu réfléchis toujours avant de répondre.\n"
                        "Si une question est imprévue, reste calme et bienveillante, et donne la meilleure réponse possible avec intelligence."
                    )
                },
                {"role": "user", "content": user_input}
            ],
            model="llama3-8b-8192",
            temperature=0.5
        )

        return chat_completion.choices[0].message.content

    except Exception as e:
        return f"Désolée, je rencontre un petit souci pour répondre. N'hésite pas à réessayer dans quelques instants. (Erreur : {str(e)})"
