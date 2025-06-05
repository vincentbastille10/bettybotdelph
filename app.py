from flask import Flask, request, jsonify, send_from_directory, render_template
from flask_cors import CORS
import os
from dotenv import load_dotenv
from chatbot_core import get_bot_response

# Charger les variables d'environnement
load_dotenv()

app = Flask(__name__, static_folder="static")
CORS(app)

@app.route("/")
def index():
    return render_template("widget.html")

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_message = data.get("question", "")

    if not user_message:
        return jsonify({"error": "Message utilisateur manquant."}), 400

    try:
        bot_response = get_bot_response(user_message)
        return jsonify({"response": bot_response})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory("static", filename)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
