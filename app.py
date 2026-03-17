import os
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"
os.environ["REQUESTS_CA_BUNDLE"] = ""
os.environ["CURL_CA_BUNDLE"] = ""

import ssl
ssl._create_default_https_context = ssl._create_unverified_context

import urllib3
urllib3.disable_warnings()

# ── Patch HTTPAdapter BEFORE any other imports ────────
import requests
original_send = requests.adapters.HTTPAdapter.send
def patched_send(self, request, **kwargs):
    kwargs["verify"] = False
    return original_send(self, request, **kwargs)
requests.adapters.HTTPAdapter.send = patched_send

# ── Patch OAuth2Session fetch_token ───────────────────
from requests_oauthlib import OAuth2Session
original_fetch = OAuth2Session.fetch_token
def patched_fetch(self, *args, **kwargs):
    kwargs["verify"] = False
    return original_fetch(self, *args, **kwargs)
OAuth2Session.fetch_token = patched_fetch

import pickle
import shutil
from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_dance.contrib.google import make_google_blueprint, google
from flask_dance.consumer import oauth_authorized
from dotenv import load_dotenv
from models import User
from rag.chunker import load_and_chunk
from rag.embeddings import store_embeddings
from rag.retriever import retrieve_chunks
from rag.generator import generate_answer
from config import SECRET_KEY, MONGO_URI, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET

# ── Init ─────────────────────────────────────────────
load_dotenv()
app = Flask(__name__)

app.config["SECRET_KEY"] = SECRET_KEY
app.config["UPLOAD_FOLDER"] = "uploads"

META_PATH = os.path.join("vectorstore", "metadata.pkl")

os.makedirs("uploads", exist_ok=True)
os.makedirs("vectorstore", exist_ok=True)

# ── Google Blueprint ──────────────────────────────────
google_bp = make_google_blueprint(
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    scope=["openid", "profile", "email"],
)
app.register_blueprint(google_bp, url_prefix="/login")

# ── Database & Login Manager ──────────────────────────
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

chat_history = {}

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

# ── Google OAuth Signal Handler ───────────────────────
@oauth_authorized.connect_via(google_bp)
def google_logged_in(blueprint, token):
    if not token:
        return False

    try:
        resp = blueprint.session.get("/oauth2/v2/userinfo")
        if not resp.ok:
            return False

        google_info = resp.json()
        email = google_info.get("email")
        name = google_info.get("name", "")
        picture = google_info.get("picture","")
        username = name.replace(" ", "_").lower() if name else email.split("@")[0]

        if not email:
            return False

        with app.app_context():
            user = User.find_by_email(email)

            if not user:
                if User.find_by_username(username):
                    username = username + "_g"

                user = User(
                    username=username,
                    email=email,
                    profile_pic=picture
                )
                user.set_password(os.urandom(24).hex())
                user.save()
            else:
                if picture and user.profile_pic != picture:
                    user.profile_pic = picture
                    user.save()

            login_user(user)

    except Exception as e:
        print(f"Google login error: {e}")

    return False

@app.route("/upload_profile_pic", methods=["POST"])
@login_required
def upload_profile_pic():
    try:
        if "profile_pic" not in request.files:
            return jsonify({"error": "No file found"}), 400

        file = request.files["profile_pic"]

        if file.filename == "":
            return jsonify({"error": "No file selected"}), 400

        # ── Check file type ──
        allowed = {"png", "jpg", "jpeg", "gif", "webp"}
        ext = file.filename.rsplit(".", 1)[1].lower()
        if ext not in allowed:
            return jsonify({"error": "Only image files allowed"}), 400

        # ── Save profile pic ──
        pic_folder = os.path.join("static", "profile_pics")
        os.makedirs(pic_folder, exist_ok=True)

        filename = f"{current_user.username}.{ext}"
        filepath = os.path.join(pic_folder, filename)
        file.save(filepath)

        current_user.profile_pic = f"/static/profile_pics/{filename}"
        current_user.save()

        return jsonify({
            "message": "Profile picture updated!",
            "profile_pic": current_user.profile_pic
        }), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

@app.route("/get_profile", methods=["GET"])
@login_required
def get_profile():
    return jsonify({
        "username": current_user.username,
        "profile_pic": current_user.profile_pic or ""
    }), 200

# ── Helper Functions ──────────────────────────────────
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in {"pdf", "docx", "txt", "md"}

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

        if User.find_by_username(username):
            return render_template("register.html", error="Username already exists!")

        if User.find_by_email(email):
            return render_template("register.html", error="Email already exists!")

        user = User(username=username, email=email)
        user.set_password(password)
        user.save()
        return redirect(url_for("login"))

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        data = request.form
        username = data.get("username")
        password = data.get("password")

        user = User.find_by_username(username)

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

@app.route("/admin", methods=["GET"])
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        return "Unauthorized", 403
    users = User.get_all()
    user_files = {}
    for user in users:
        folder = get_user_upload_folder(user.username)
        if os.path.exists(folder):
            user_files[user.username] = [f for f in os.listdir(folder) if f.endswith((".pdf", ".docx", ".txt", ".md"))]
        else:
            user_files[user.username] = []
    
    return render_template("admin.html", users=users, user_files=user_files)

@app.route("/download/<username>/<filename>")
@login_required
def download_file(username, filename):
    # Only the owner or an admin can download
    if current_user.username != username and not current_user.is_admin:
        return "Unauthorized", 403
        
    folder = get_user_upload_folder(username)
    filepath = os.path.join(folder, filename)
    if not os.path.exists(filepath):
        return "File not found", 404
        
    from flask import send_file
    return send_file(filepath, as_attachment=True)

@app.route("/profile", methods=["GET"])
@login_required
def profile():
    return render_template("profile.html", current_user=current_user)

@app.route("/update_settings", methods=["POST"])
@login_required
def update_settings():
    try:
        data = request.get_json()
        current_user.preferred_model = data.get("preferred_model", "groq")
        
        # Determine if we are deleting keys or setting new ones
        groq_req = data.get("groq_key", "").strip()
        gemini_req = data.get("gemini_key", "").strip()
        
        if groq_req == "DELETE":
            current_user.set_groq_key(None)
        elif groq_req:
            current_user.set_groq_key(groq_req)
            
        if gemini_req == "DELETE":
            current_user.set_gemini_key(None)
        elif gemini_req:
            current_user.set_gemini_key(gemini_req)
        
        current_user.save()
        return jsonify({"message": "Settings updated successfully!"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/files", methods=["GET"])
@login_required
def get_files():
    try:
        folder = get_user_upload_folder(current_user.username)
        files = [f for f in os.listdir(folder) if f.endswith((".pdf", ".docx", ".txt", ".md"))]
        return jsonify({"files": files}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/upload", methods=["POST"])
@login_required
def upload():
    try:
        if not current_user.get_groq_key() and not current_user.get_gemini_key():
            return jsonify({"error": "⚠️ Please add your Groq or Gemini API key in the Profile page to upload and chat."}), 400

        if "pdf" not in request.files:
            return jsonify({"error": "No file found"}), 400

        file = request.files["pdf"]

        if file.filename == "":
            return jsonify({"error": "No file selected"}), 400

        if not allowed_file(file.filename):
            return jsonify({"error": "Only PDF, DOCX, TXT & MD files allowed"}), 400

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
        if not current_user.get_groq_key() and not current_user.get_gemini_key():
            return jsonify({"error": "⚠️ Please add your Groq or Gemini API key in the Profile page to upload and chat."}), 400

        data = request.get_json()
        question = data.get("question", "").strip()
        filename = data.get("filename", "").strip()

        if not question:
            return jsonify({"error": "Question cannot be empty"}), 400

        meta_path = get_user_meta_path(current_user.username)
        context_chunks = retrieve_chunks(question, filename, meta_path)
        answer = generate_answer(question, context_chunks, current_user)

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