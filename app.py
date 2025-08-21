import os
import openai
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Vérifier que la clé existe
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("❌ Aucune clé API trouvée. Vérifie ton .env ou Render Environment.")

# Configurer OpenAI
openai.api_key = api_key

# Créer l'app Flask
app = Flask(__name__)

@app.route("/")
def home():
    return "✅ API Flask + OpenAI (0.28) fonctionne."

@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.json
        user_message = data.get("message", "")

        if not user_message:
            return jsonify({"error": "Message manquant"}), 400

        # Appel API OpenAI
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",   # ou "gpt-4" si dispo
            messages=[{"role": "user", "content": user_message}],
            max_tokens=200
        )

        bot_reply = response["choices"][0]["message"]["content"]
        return jsonify({"reply": bot_reply})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
