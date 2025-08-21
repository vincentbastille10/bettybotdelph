import os
import openai
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# Charger les variables d'environnement (.env en local, Render en prod)
load_dotenv()

# Vérifie quelle clé est dispo
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")

if OPENAI_KEY:
    openai.api_key = OPENAI_KEY
    openai.api_base = "https://api.openai.com/v1"
    MODEL_ID = os.getenv("MODEL_ID", "gpt-3.5-turbo")
elif OPENROUTER_KEY:
    openai.api_key = OPENROUTER_KEY
    openai.api_base = "https://openrouter.ai/api/v1"
    MODEL_ID = os.getenv("MODEL_ID", "openai/gpt-4o-mini")
else:
    raise ValueError("❌ Aucune clé API trouvée (ni OPENAI_API_KEY ni OPENROUTER_API_KEY)")

# Flask app
app = Flask(__name__)

@app.route("/")
def home():
    provider = "OpenAI" if OPENAI_KEY else "OpenRouter"
    return f"✅ Flask OK — Provider: {provider} — Model: {MODEL_ID}"

@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json(force=True)
        user_message = (data or {}).get("message", "").strip()

        if not user_message:
            return jsonify({"error": "Message manquant"}), 400

        resp = openai.ChatCompletion.create(
            model=MODEL_ID,
            messages=[{"role": "user", "content": user_message}],
            max_tokens=200,
        )
        bot_reply = resp["choices"][0]["message"]["content"].strip()
        return jsonify({"reply": bot_reply})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
