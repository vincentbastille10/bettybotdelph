import os
import openai
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# ----- CORS facultatif (ne casse pas si non installé) -----
try:
    from flask_cors import CORS  # type: ignore
    _HAS_CORS = True
except Exception:
    _HAS_CORS = False

# ----- ENV / Provider -----
load_dotenv()

OPENAI_KEY = os.getenv("OPENAI_API_KEY")
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")

if OPENAI_KEY:
    openai.api_key = OPENAI_KEY
    openai.api_base = "https://api.openai.com/v1"
    PROVIDER = "OpenAI"
    MODEL_ID = os.getenv("MODEL_ID", "gpt-3.5-turbo")
    FALLBACK_MODEL = os.getenv("FALLBACK_MODEL", "gpt-3.5-turbo")
elif OPENROUTER_KEY:
    openai.api_key = OPENROUTER_KEY
    openai.api_base = "https://openrouter.ai/api/v1"
    PROVIDER = "OpenRouter"
    MODEL_ID = os.getenv("MODEL_ID", "openai/gpt-4o-mini")
    FALLBACK_MODEL = os.getenv("FALLBACK_MODEL", "anthropic/claude-3-5-sonnet-20240620")
else:
    raise ValueError("❌ Aucune clé API (ni OPENAI_API_KEY ni OPENROUTER_API_KEY)")

# ----- Flask -----
app = Flask(__name__)
if _HAS_CORS:
    CORS(app, resources={r"/chat": {"origins": "*"}})

@app.route("/")
def home():
    return f"✅ Flask OK — Provider: {PROVIDER} — Model: {MODEL_ID}"

@app.route("/healthz")
def healthz():
    return "OK", 200

def _extract_message(payload: dict) -> str:
    """Accepte plusieurs noms de champs (évite les 400)."""
    for key in ("message", "text", "content", "prompt"):
        val = payload.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return ""

def _call_model(model: str, user_message: str) -> str:
    """Appel unique (API openai==0.28 compatible)."""
    resp = openai.ChatCompletion.create(
        model=model,
        messages=[{"role": "user", "content": user_message}],
        max_tokens=300,
        temperature=0.4,
    )
    return resp["choices"][0]["message"]["content"].strip()

@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json(force=True) or {}
        user_message = _extract_message(data)
        if not user_message:
            return jsonify({"error": "Message manquant (keys acceptées: message|text|content|prompt)"}), 400

        # Essai modèle principal
        try:
            reply = _call_model(MODEL_ID, user_message)
            return jsonify({"reply": reply, "model_used": MODEL_ID})
        except Exception as e1:
            # Fallback
            if FALLBACK_MODEL and FALLBACK_MODEL != MODEL_ID:
                reply = _call_model(FALLBACK_MODEL, user_message)
                return jsonify({"reply": reply, "model_used": FALLBACK_MODEL})
            return jsonify({"error": str(e1)}), 500

    except Exception as e:
        app.logger.exception("Unhandled /chat error")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
