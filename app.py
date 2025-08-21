import os
import openai
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

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
    # modèle principal + fallback côté OpenRouter
    MODEL_ID = os.getenv("MODEL_ID", "openai/gpt-4o-mini")
    FALLBACK_MODEL = os.getenv("FALLBACK_MODEL", "anthropic/claude-3-5-sonnet-20240620")
else:
    raise ValueError("❌ Aucune clé API trouvée (ni OPENAI_API_KEY ni OPENROUTER_API_KEY)")

# ----- Flask -----
app = Flask(__name__)
CORS(app, resources={r"/chat": {"origins": "*"}})

@app.route("/")
def home():
    return f"✅ Flask OK — Provider: {PROVIDER} — Model: {MODEL_ID}"

@app.route("/healthz")
def healthz():
    return "OK", 200

def _call_model(model: str, user_message: str) -> str:
    """Appel unique au modèle (API openai==0.28 compatible)."""
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
        user_message = (data.get("message") or "").strip()
        if not user_message:
            return jsonify({"error": "Message manquant"}), 400

        # 1) Essai avec le modèle principal
        try:
            reply = _call_model(MODEL_ID, user_message)
            return jsonify({"reply": reply})
        except Exception as e1:
            # 2) Fallback si on est sur OpenRouter (souvent erreur de modèle)
            try:
                app.logger.warning(f"Primary model failed ({MODEL_ID}): {e1}")
                if FALLBACK_MODEL and FALLBACK_MODEL != MODEL_ID:
                    reply = _call_model(FALLBACK_MODEL, user_message)
                    return jsonify({"reply": reply, "model_used": FALLBACK_MODEL})
                # si pas de fallback ou identique → relancer l'erreur
                raise
            except Exception as e2:
                app.logger.error(f"Fallback failed ({FALLBACK_MODEL}): {e2}")
                return jsonify({"error": f"{str(e1)}"}), 500

    except Exception as e:
        app.logger.exception("Unhandled /chat error")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
