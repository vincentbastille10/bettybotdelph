import os
from flask import Flask, request, jsonify
from openai import OpenAI

# Création du client OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Choix du modèle : soit variable d'environnement, soit par défaut gpt-4o-mini
MODEL_ID = os.getenv("MODEL_ID", "gpt-4o-mini")

# Création de l'app Flask
app = Flask(__name__)

@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        user_message = data.get("message", "")

        if not user_message:
            return jsonify({"error": "Aucun message reçu"}), 400

        # Requête au modèle OpenAI
        response = client.chat.completions.create(
            model=MODEL_ID,
            messages=[
                {"role": "system", "content": "Tu es Betty, une assistante gentille et serviable."},
                {"role": "user", "content": user_message}
            ]
        )

        bot_reply = response.choices[0].message.content
        return jsonify({"reply": bot_reply})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
