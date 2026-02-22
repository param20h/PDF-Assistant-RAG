import os
import pickle
import shutil
from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from dotenv import load_dotenv
from models import db, User
from rag.chunker import load_and_chunk
from rag.embeddings import store_embeddings
from rag.retriever import retrieve_chunks
from rag.generator import generate_answer
from config import SECRET_KEY, SQLALCHEMY_DATABASE_URI

# ── Init ─────────────────────────────────────────────
load_dotenv()
app = Flask(__name__)

app.config["SECRET_KEY"] = SECRET_KEY
app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
app.config["UPLOAD_FOLDER"] = "uploads"

META_PATH = os.path.join("vectorstore", "metadata.pkl")

os.makedirs("uploads", exist_ok=True)
os.makedirs("vectorstore", exist_ok=True)

# ── Database & Login Manager ──────────────────────────
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

chat_history = {}

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ── Create DB ─────────────────────────────────────────
with app.app_context():
    db.create_all()

# ── Helper ────────────────────────────────────────────
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in {"pdf"}

def get_user_upload_folder(username):
    folder = os.path.join("uploads", username)
    os.makedirs(folder, exist_ok=True)
    return folder

def get_user_meta_path(username):
    path = os.path.join("vectorstore", username)
    os.makedirs(path, exist_ok=True)
    return os.path.join(path, "metadata.pkl")

# ── Auth Routes ───────────────────────────────────────

@app.route("/")
@login_required
def index():
    return render_template("index.html", username=current_user.username)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        data = request.form
        username = data.get("username")
        email = data.get("email")
        password = data.get("password")

        if User.query.filter_by(username=username).first():
            return render_template("register.html", error="Username already exists!")

        if User.query.filter_by(email=email).first():
            return render_template("register.html", error="Email already exists!")

        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        return redirect(url_for("login"))

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        data = request.form
        username = data.get("username")
        password = data.get("password")

        user = User.query.filter_by(username=username).first()

        if not user or not user.check_password(password):
            return render_template("login.html", error="Invalid username or password!")

        login_user(user)
        return redirect(url_for("index"))

    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

# ── App Routes ────────────────────────────────────────

@app.route("/chat")
@login_required
def chat():
    return render_template("chat.html", username=current_user.username)

@app.route("/files", methods=["GET"])
@login_required
def get_files():
    try:
        folder = get_user_upload_folder(current_user.username)
        files = [f for f in os.listdir(folder) if f.endswith(".pdf")]
        return jsonify({"files": files}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    try:
        if "pdf" not in request.files:
            return jsonify({"error": "No file found"}), 400

        file = request.files["pdf"]

        if file.filename == "":
            return jsonify({"error": "No file selected"}), 400

        if not allowed_file(file.filename):
            return jsonify({"error": "Only PDF files allowed"}), 400

        folder = get_user_upload_folder(current_user.username)
        filepath = os.path.join(folder, file.filename)
        file.save(filepath)

        meta_path = get_user_meta_path(current_user.username)
        chunks = load_and_chunk(filepath)
        store_embeddings(chunks, file.filename, meta_path)

        return jsonify({"message": f"{file.filename} uploaded successfully!"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/ask", methods=["POST"])
@login_required
def ask():
    try:
        data = request.get_json()
        question = data.get("question", "").strip()
        filename = data.get("filename", "").strip()

        if not question:
            return jsonify({"error": "Question cannot be empty"}), 400

        meta_path = get_user_meta_path(current_user.username)
        context_chunks = retrieve_chunks(question, filename, meta_path)
        answer = generate_answer(question, context_chunks)

        username = current_user.username
        if username not in chat_history:
            chat_history[username] = []

        chat_history[username].append({
            "question": question,
            "answer": answer
        })

        return jsonify({
            "answer": answer,
            "sources": context_chunks
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/history", methods=["GET"])
@login_required
def history():
    try:
        username = current_user.username
        return jsonify({"history": chat_history.get(username, [])}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/clear", methods=["POST"])
@login_required
def clear():
    try:
        username = current_user.username
        chat_history[username] = []
        return jsonify({"message": "Chat history cleared!"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/delete", methods=["POST"])
@login_required
def delete():
    try:
        data = request.get_json()
        filename = data.get("filename", "")

        if not filename:
            return jsonify({"error": "Filename not provided"}), 400

        folder = get_user_upload_folder(current_user.username)
        filepath = os.path.join(folder, filename)

        if not os.path.exists(filepath):
            return jsonify({"error": "File not found"}), 404

        os.remove(filepath)

        meta_path = get_user_meta_path(current_user.username)
        if os.path.exists(meta_path):
            with open(meta_path, "rb") as f:
                metadata = pickle.load(f)
            new_metadata = [m for m in metadata if m["filename"] != filename]
            with open(meta_path, "wb") as f:
                pickle.dump(new_metadata, f)

        return jsonify({"message": f"{filename} deleted successfully!"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/clear_vectorstore", methods=["POST"])
@login_required
def clear_vectorstore():
    try:
        username = current_user.username
        vectorstore_path = os.path.join("vectorstore", username)

        if os.path.exists(vectorstore_path):
            shutil.rmtree(vectorstore_path)
            os.makedirs(vectorstore_path, exist_ok=True)

        return jsonify({"message": "Vector store cleared successfully!"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── Run ───────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)