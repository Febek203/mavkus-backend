"""
Firebase Service per MAVKUS AI
"""
import os
import logging
from datetime import datetime
from typing import Dict, Optional, List, Any

from cryptography.fernet import Fernet
from dotenv import load_dotenv

# =========================
# CONFIGURAZIONE
# =========================
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("FirebaseService")

# =========================
# INIZIALIZZAZIONE FIREBASE
# =========================
try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    
    # Verifica variabili ambiente
    required_vars = ["FIREBASE_PROJECT_ID", "FIREBASE_PRIVATE_KEY", "FIREBASE_CLIENT_EMAIL"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"❌ Variabili Firebase mancanti: {missing_vars}")
        raise ValueError(f"Variabili Firebase mancanti: {missing_vars}")
    
    # Configura credenziali
    firebase_config = {
        "type": "service_account",
        "project_id": os.getenv("FIREBASE_PROJECT_ID"),
        "private_key": os.getenv("FIREBASE_PRIVATE_KEY").replace("\\n", "\n"),
        "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
        "token_uri": "https://oauth2.googleapis.com/token"
    }
    
    if not firebase_admin._apps:
        cred = credentials.Certificate(firebase_config)
        firebase_admin.initialize_app(cred)
    
    db = firestore.client()
    FIREBASE_AVAILABLE = True
    logger.info("✅ Firebase inizializzato correttamente")
    
except Exception as e:
    logger.error(f"❌ Errore inizializzazione Firebase: {e}")
    FIREBASE_AVAILABLE = False
    db = None

# =========================
# SERVIZIO DI CRITTAZIONE
# =========================
class EncryptionService:
    def __init__(self):
        key = os.getenv("ENCRYPTION_KEY")
        if not key:
            logger.error("❌ ENCRYPTION_KEY mancante! Genera con:")
            logger.error('python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"')
            raise ValueError("ENCRYPTION_KEY mancante")
        
        try:
            self.cipher = Fernet(key.encode())
            logger.info("✅ Servizio crittografia inizializzato")
        except Exception as e:
            logger.error(f"❌ Errore inizializzazione crittografia: {e}")
            raise
    
    def encrypt(self, value: str) -> str:
        """Cripta una stringa"""
        if not value:
            return ""
        return self.cipher.encrypt(value.encode()).decode()
    
    def decrypt(self, value: str) -> str:
        """Decripta una stringa"""
        if not value:
            return ""
        return self.cipher.decrypt(value.encode()).decode()

# =========================
# SERVIZIO FIREBASE PRINCIPALE
# =========================
class FirebaseService:
    def __init__(self):
        self.available = FIREBASE_AVAILABLE
        self.crypto = EncryptionService()
        logger.info(f"📊 Firebase Service: {'✅ Disponibile' if self.available else '❌ Non disponibile'}")
    
    # ---------- GESTIONE UTENTI ----------
    def create_user_profile(self, user_id: str, email: str, display_name: str = None, photo_url: str = None) -> Dict[str, Any]:
        """Crea o aggiorna profilo utente"""
        if not self.available:
            return {"success": False, "error": "firebase_unavailable"}
        
        try:
            user_ref = db.collection("users").document(user_id)
            now = datetime.utcnow().isoformat()
            
            user_data = {
                "user_id": user_id,
                "email": email,
                "display_name": display_name or "",
                "photo_url": photo_url or "",
                "created_at": now,
                "last_login": now,
                "total_conversations": 0,
                "total_tokens_used": 0,
                "plan": "free",
                "api_keys_configured": False,
                "updated_at": now
            }
            
            # Verifica se esiste già
            existing = user_ref.get()
            if existing.exists:
                # Aggiorna solo alcuni campi
                user_ref.update({
                    "last_login": now,
                    "display_name": display_name or existing.to_dict().get("display_name", ""),
                    "photo_url": photo_url or existing.to_dict().get("photo_url", ""),
                    "updated_at": now
                })
                action = "aggiornato"
            else:
                # Crea nuovo
                user_ref.set(user_data)
                action = "creato"
            
            logger.info(f"👤 Profilo utente {action}: {user_id[:8]}...")
            return {"success": True, "action": action}
            
        except Exception as e:
            logger.error(f"❌ Errore creazione profilo utente: {e}")
            return {"success": False, "error": str(e)}
    
    def get_user(self, user_id: str) -> Optional[Dict]:
        """Ottieni dati utente"""
        try:
            doc = db.collection("users").document(user_id).get()
            if doc.exists:
                return doc.to_dict()
            return None
        except Exception as e:
            logger.error(f"❌ Errore get_user: {e}")
            return None
    
    # ---------- GESTIONE API KEYS ----------
    def save_api_keys(self, user_id: str, api_keys: Dict[str, str]) -> bool:
        """Salva API keys criptate"""
        try:
            encrypted_keys = {}
            
            # Cripta solo se presenti
            if api_keys.get("groq_api_key"):
                encrypted_keys["groq"] = self.crypto.encrypt(api_keys["groq_api_key"])
            
            if api_keys.get("gemini_api_key"):
                encrypted_keys["gemini"] = self.crypto.encrypt(api_keys["gemini_api_key"])
            
            # Salva su Firestore
            db.collection("users").document(user_id).update({
                "api_keys": encrypted_keys,
                "api_keys_configured": len(encrypted_keys) > 0,
                "updated_at": datetime.utcnow().isoformat()
            })
            
            logger.info(f"🔑 API keys salvate per utente: {user_id[:8]}...")
            return True
            
        except Exception as e:
            logger.error(f"❌ Errore save_api_keys: {e}")
            return False
    
    def get_api_keys(self, user_id: str) -> Dict[str, str]:
        """Ottieni API keys decriptate"""
        try:
            doc = db.collection("users").document(user_id).get()
            if not doc.exists:
                return {}
            
            data = doc.to_dict()
            encrypted_keys = data.get("api_keys", {})
            
            decrypted_keys = {}
            if "groq" in encrypted_keys:
                decrypted_keys["groq_api_key"] = self.crypto.decrypt(encrypted_keys["groq"])
            
            if "gemini" in encrypted_keys:
                decrypted_keys["gemini_api_key"] = self.crypto.decrypt(encrypted_keys["gemini"])
            
            return decrypted_keys
            
        except Exception as e:
            logger.error(f"❌ Errore get_api_keys: {e}")
            return {}
    
    # ---------- GESTIONE CONVERSAZIONI ----------
    def save_conversation(self, user_id: str, conversation_data: Dict) -> str:
        """Salva una conversazione"""
        try:
            conv_ref = db.collection("users").document(user_id)\
                .collection("conversations").document()
            
            # Aggiungi metadati
            conversation_data["id"] = conv_ref.id
            conversation_data["created_at"] = datetime.utcnow().isoformat()
            conversation_data["user_id"] = user_id
            
            # Salva
            conv_ref.set(conversation_data)
            
            # Aggiorna contatore utente
            user_ref = db.collection("users").document(user_id)
            user_ref.update({
                "total_conversations": firestore.Increment(1),
                "updated_at": datetime.utcnow().isoformat()
            })
            
            logger.info(f"💾 Conversazione salvata: {conv_ref.id}")
            return conv_ref.id
            
        except Exception as e:
            logger.error(f"❌ Errore save_conversation: {e}")
            return ""
    
    def get_conversations(self, user_id: str, limit: int = 20) -> List[Dict]:
        """Ottieni ultime conversazioni"""
        try:
            convs_ref = db.collection("users").document(user_id)\
                .collection("conversations")\
                .order_by("created_at", direction=firestore.Query.DESCENDING)\
                .limit(limit)
            
            conversations = []
            for doc in convs_ref.stream():
                conv_data = doc.to_dict()
                conv_data["id"] = doc.id
                conversations.append(conv_data)
            
            return conversations
            
        except Exception as e:
            logger.error(f"❌ Errore get_conversations: {e}")
            return []
    
    def delete_conversation(self, user_id: str, conversation_id: str) -> bool:
        """Elimina una conversazione"""
        try:
            db.collection("users").document(user_id)\
                .collection("conversations").document(conversation_id).delete()
            
            # Aggiorna contatore
            user_ref = db.collection("users").document(user_id)
            user_ref.update({
                "total_conversations": firestore.Increment(-1),
                "updated_at": datetime.utcnow().isoformat()
            })
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Errore delete_conversation: {e}")
            return False
    
    # ---------- STATISTICHE ----------
    def update_token_usage(self, user_id: str, tokens_used: int):
        """Aggiorna contatore token"""
        try:
            db.collection("users").document(user_id).update({
                "total_tokens_used": firestore.Increment(tokens_used),
                "updated_at": datetime.utcnow().isoformat()
            })
        except Exception as e:
            logger.error(f"❌ Errore update_token_usage: {e}")

# =========================
# ISTANZA GLOBALE
# =========================
firebase_service = FirebaseService()