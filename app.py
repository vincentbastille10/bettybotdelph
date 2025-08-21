import os
import openai
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv

load_dotenv()

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
    raise ValueError("Aucune clé API (OPENAI_API_KEY ou OPENROUTER_API_KEY)")

app = Flask(__name__, static_folder="static", template_folder="templates")

@app.route("/")
def home():
    return render_template("widget.html")

def _extract_msg(payload: dict) -> str:
    # accepte plusieurs keys pour éviter les 400 silencieux
    for k in ("message", "text", "content", "prompt", "msg"):
        v = payload.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""

def _call(model: str, text: str) -> str:
    r = openai.ChatCompletion.create(
        model=model,
        messages=[{"role": "user", "content": text}],
        max_tokens=300,
        temperature=0.4,
    )
    return r["choices"][0]["message"]["content"].strip()

@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json(force=True) or {}
        user_text = _extract_msg(data)
        if not user_text:
            return jsonify({"error": "Message manquant (keys acceptées: message|text|content|prompt|msg)"}), 400

        try:
            reply = _call(MODEL_ID, user_text)
            return jsonify({"reply": reply})
        except Exception as e1:
            # petit fallback simple si le modèle principal ne répond pas
            fb = os.getenv("FALLBACK_MODEL", "anthropic/claude-3-5-sonnet-20240620")
            if fb and fb != MODEL_ID:
                try:
                    reply = _call(fb, user_text)
                    return jsonify({"reply": reply, "model_used": fb})
                except Exception as e2:
                    return jsonify({"error": f"{e1} | fallback: {e2}"}), 500
            return jsonify({"error": str(e1)}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/healthz")
def healthz():
    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
