import os
import openai
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv

# Charger les variables d’environnement
load_dotenv()

# --- Détection Provider ---
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")

if OPENAI_KEY:
    openai.api_key = OPENAI_KEY
    openai.api_base = "https://api.openai.com/v1"
    PROVIDER = "OpenAI"
    MODEL_ID = os.getenv("MODEL_ID", "gpt-3.5-turbo")
elif OPENROUTER_KEY:
    openai.api_key = OPENROUTER_KEY
    openai.api_base = "https://openrouter.ai/api/v1"
    PROVIDER = "OpenRouter"
    MODEL_ID = os.getenv("MODEL_ID", "openai/gpt-4o-mini")
else:
    raise ValueError("❌ Aucune clé API trouvée (OPENAI_API_KEY ou OPENROUTER_API_KEY)")

# --- Flask ---
app = Flask(__name__, static_folder="static", template_folder="templates")

@app.route("/")
def home():
    return render_template("widget.html")  # ton interface de chat

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(force=True)
    user_msg = (data.get("message") or "").strip()
    if not user_msg:
        return jsonify({"error": "Message vide"}), 400

    try:
        resp = openai.ChatCompletion.create(
            model=MODEL_ID,
            messages=[{"role": "user", "content": user_msg}],
            max_tokens=400,
            temperature=0.4
        )
        reply = resp["choices"][0]["message"]["content"].strip()
        return jsonify({"reply": reply})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/healthz")
def healthz():
    return f"Flask OK — Provider: {PROVIDER} — Model: {MODEL_ID}", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
