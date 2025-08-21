import os
import openai
from dotenv import load_dotenv

# Charger les variables d'environnement (.env)
load_dotenv()

# Configurer la clé API
openai.api_key = os.getenv("OPENAI_API_KEY")

def ask_betty(prompt: str) -> str:
    """
    Envoie une requête au modèle GPT et renvoie la réponse texte.
    Compatible avec openai==0.28
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # ou "gpt-4" si dispo sur ton compte
            messages=[
                {"role": "system", "content": "Tu es Betty, une assistante gentille et efficace."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.7
        )

        # Récupérer uniquement le texte de la réponse
        return response["choices"][0]["message"]["content"].strip()

    except Exception as e:
        return f"❌ Erreur dans BettyBot : {str(e)}"
