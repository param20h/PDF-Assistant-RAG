from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from cryptography.fernet import Fernet
import pymongo
from bson.objectid import ObjectId
from config import ENCRYPTION_KEY, MONGO_URI

# Connect to MongoDB
mongo_client = pymongo.MongoClient(MONGO_URI)
try:
    db = mongo_client.get_default_database()
except pymongo.errors.ConfigurationError:
    db = mongo_client["rag_app"]

users_collection = db["users"]
cipher_suite = Fernet(ENCRYPTION_KEY)

class User(UserMixin):
    def __init__(self, username, email, password=None, _id=None, google_id=None,
                 profile_pic=None, groq_api_key=None, gemini_api_key=None,
                 pinecone_api_key=None, pinecone_index_name=None,
                 preferred_model="groq", is_admin=False):
        self.username = username
        self.email = email
        self.password = password
        self.google_id = google_id
        self.profile_pic = profile_pic
        self.groq_api_key = groq_api_key
        self.gemini_api_key = gemini_api_key
        self.pinecone_api_key = pinecone_api_key
        self.pinecone_index_name = pinecone_index_name or ""
        self.preferred_model = preferred_model
        self.is_admin = is_admin
        if _id:
            self.id = str(_id)
        else:
            self.id = None

    def get_id(self):
        return self.id or self.username

    def save(self):
        user_data = {
            "username": self.username,
            "email": self.email,
            "password": self.password,
            "google_id": self.google_id,
            "profile_pic": self.profile_pic,
            "groq_api_key": self.groq_api_key,
            "gemini_api_key": self.gemini_api_key,
            "pinecone_api_key": self.pinecone_api_key,
            "pinecone_index_name": self.pinecone_index_name,
            "preferred_model": self.preferred_model,
            "is_admin": self.is_admin
        }
        
        if self.id:
            users_collection.update_one({"_id": ObjectId(self.id)}, {"$set": user_data})
        else:
            result = users_collection.insert_one(user_data)
            self.id = str(result.inserted_id)
            
    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

    # ── Groq Key ─────────────────────────────────────
    def set_groq_key(self, api_key):
        if api_key:
            self.groq_api_key = cipher_suite.encrypt(api_key.encode('utf-8')).decode('utf-8')
        else:
            self.groq_api_key = None

    def get_groq_key(self):
        if self.groq_api_key:
            try:
                return cipher_suite.decrypt(self.groq_api_key.encode('utf-8')).decode('utf-8')
            except Exception:
                return None
        return None

    # ── Gemini Key ───────────────────────────────────
    def set_gemini_key(self, api_key):
        if api_key:
            self.gemini_api_key = cipher_suite.encrypt(api_key.encode('utf-8')).decode('utf-8')
        else:
            self.gemini_api_key = None

    def get_gemini_key(self):
        if self.gemini_api_key:
            try:
                return cipher_suite.decrypt(self.gemini_api_key.encode('utf-8')).decode('utf-8')
            except Exception:
                return None
        return None

    # ── Pinecone Key ─────────────────────────────────
    def set_pinecone_key(self, api_key):
        if api_key:
            self.pinecone_api_key = cipher_suite.encrypt(api_key.encode('utf-8')).decode('utf-8')
        else:
            self.pinecone_api_key = None

    def get_pinecone_key(self):
        if self.pinecone_api_key:
            try:
                return cipher_suite.decrypt(self.pinecone_api_key.encode('utf-8')).decode('utf-8')
            except Exception:
                return None
        return None

    @classmethod
    def get(cls, user_id):
        try:
            data = users_collection.find_one({"_id": ObjectId(user_id)})
            if data:
                return cls(**data)
            return None
        except Exception:
            return None

    @classmethod
    def find_by_username(cls, username):
        data = users_collection.find_one({"username": username})
        if data:
            return cls(**data)
        return None

    @classmethod
    def find_by_email(cls, email):
        data = users_collection.find_one({"email": email})
        if data:
            return cls(**data)
        return None

    @classmethod
    def get_all(cls):
        return [cls(**data) for data in users_collection.find()]