import os
import openai
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv

# ----- ENV -----
load_dotenv()
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
    raise ValueError("Aucune clé API (OPENAI_API_KEY ou OPENROUTER_API_KEY)")

# ----- Flask -----
app = Flask(__name__, static_folder="static", template_folder="templates")

# Page d’accueil = UI du chat
@app.route("/")
def home():
    return render_template("index.html", provider=PROVIDER, model=MODEL_ID)

# API chat (POST)
def _call_model(model: str, user_message: str) -> str:
    resp = openai.ChatCompletion.create(
        model=model,
        messages=[{"role": "user", "content": user_message}],
        max_tokens=300,
        temperature=0.4,
    )
    return resp["choices"][0]["message"]["content"].strip()

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(force=True) or {}
    text = (data.get("message") or data.get("text") or data.get("content") or data.get("prompt") or "").strip()
    if not text:
        return jsonify({"error": "Message manquant"}), 400
    try:
        reply = _call_model(MODEL_ID, text)
        return jsonify({"reply": reply})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/healthz")
def healthz():
    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
