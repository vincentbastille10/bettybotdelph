from flask import Flask, render_template, request, jsonify
from chatbot_core import get_bot_response

# Flask setup
app = Flask(__name__, static_folder='static', template_folder='static')

# Affichage de la page HTML principale (widget)
@app.route("/")
def home():
    return render_template("widget.html")

# API de dialogue
@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    question = data.get("question", "")
    response = get_bot_response(question)
    return jsonify({"response": response})

# Lancement du serveur
if __name__ == "__main__":
    app.run(debug=True)
