from flask import Flask, render_template, request, jsonify
from chatbot_core import get_bot_response
import os

# Initialisation de Flask
app = Flask(__name__, static_folder='static', template_folder='static')

# Route principale : sert la page HTML
@app.route("/")
def home():
    return render_template("widget.html")

# Route API : récupère les requêtes utilisateur
@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    question = data.get("question", "")
    response = get_bot_response(question)
    return jsonify({"response": response})

# Lancement du serveur
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Render définit la variable PORT
    app.run(host="0.0.0.0", port=port, debug=True)
