"""
FastAPI Server per MAVKUS AI
"""
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, Optional, Any
import os
import logging
from datetime import datetime
from functools import lru_cache

# Configurazione
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import servizi
from firebase_service import firebase_service
from mavkus import MavkusAI

# =========================
# MODELLI PYDANTIC
# =========================
class SaveAPIKeysRequest(BaseModel):
    user_id: str
    groq_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None

class ChatRequest(BaseModel):
    user_id: str
    message: str = Field(..., min_length=1, max_length=2000)
    enable_critique: bool = True

class InitRequest(BaseModel):
    user_id: str

class UserProfileRequest(BaseModel):
    user_id: str
    email: str
    display_name: Optional[str] = None
    photo_url: Optional[str] = None

# =========================
# FASTAPI APP
# =========================
app = FastAPI(
    title="MAVKUS AI API",
    description="API intelligente multi-AI con Groq e Gemini",
    version="3.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "https://mavkus-frontend-eta.vercel.app",
        "https://mavkus-frontend.vercel.app",
    ],
    allow_credentials=False,  # ✅ IMPORTANTE
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# DEPENDENCIES & CACHING
# =========================
@lru_cache(maxsize=100)
def _create_ai_instance(user_id: str) -> MavkusAI:
    """Factory interna per istanze AI con caching"""
    try:
        # Recupera API keys da Firebase
        api_keys = firebase_service.get_api_keys(user_id)
        
        # Crea istanza
        ai = MavkusAI(
            user_id=user_id,
            groq_api_key=api_keys.get("groq_api_key"),
            gemini_api_key=api_keys.get("gemini_api_key")
        )
        
        logger.info(f"🤖 Istanza AI creata per: {user_id[:8]}...")
        return ai
        
    except Exception as e:
        logger.error(f"❌ Errore creazione istanza AI: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def get_ai_instance(request: ChatRequest) -> MavkusAI:
    """Dependency che estrae user_id dalla request"""
    return _create_ai_instance(request.user_id)
# =========================
# HEALTH & ROOT
# =========================
@app.get("/")
async def root():
    return {
        "message": "MAVKUS AI API",
        "version": "3.0.0",
        "status": "operational",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "mavkus-ai",
        "firebase": "connected" if firebase_service.available else "disconnected",
        "timestamp": datetime.now().isoformat()
    }

# =========================
# API ENDPOINTS
# =========================
@app.post("/api/auth/create-profile")
async def create_user_profile(request: UserProfileRequest):
    """Crea/aggiorna profilo utente"""
    try:
        result = firebase_service.create_user_profile(
            user_id=request.user_id,
            email=request.email,
            display_name=request.display_name,
            photo_url=request.photo_url
        )
        
        if result["success"]:
            return {
                "success": True,
                "message": f"Profilo {result['action']}",
                "user_id": request.user_id
            }
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "Errore sconosciuto"))
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Errore create-profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/auth/save-keys")
async def save_api_keys(request: SaveAPIKeysRequest):
    """Salva API keys utente"""
    try:
        # Prepara dati
        api_keys = {}
        if request.groq_api_key:
            api_keys["groq_api_key"] = request.groq_api_key
        if request.gemini_api_key:
            api_keys["gemini_api_key"] = request.gemini_api_key
        
        # Salva su Firebase
        success = firebase_service.save_api_keys(request.user_id, api_keys)
        
        if success:
            # Invalida cache per questo utente
            get_ai_instance.cache_clear()
            
            return {
                "success": True,
                "message": "API keys salvate",
                "user_id": request.user_id,
                "keys_saved": list(api_keys.keys())
            }
        else:
            raise HTTPException(status_code=500, detail="Errore salvataggio Firebase")
            
    except Exception as e:
        logger.error(f"❌ Errore save-keys: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/auth/get-keys/{user_id}")
async def get_api_keys(user_id: str):
    """Ottieni API keys utente"""
    try:
        api_keys = firebase_service.get_api_keys(user_id)
        
        return {
            "success": True,
            "user_id": user_id,
            "api_keys": api_keys,
            "has_keys": len(api_keys) > 0
        }
        
    except Exception as e:
        logger.error(f"❌ Errore get-keys: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/init")
async def initialize_ai(request: InitRequest):
    """Inizializza MAVKUS per un utente"""
    try:
        # Verifica che l'utente esista su Firebase
        user_data = firebase_service.get_user(request.user_id)
        if not user_data:
            raise HTTPException(status_code=404, detail="Utente non trovato")
        
        # Recupera API keys salvate
        api_keys = firebase_service.get_api_keys(request.user_id)
        
        # Ottieni o crea istanza AI (usa caching)
        ai = _create_ai_instance(request.user_id) 
        
        # Ottieni statistiche
        stats = ai.get_stats()
        
        return {
            "success": True,
            "message": "MAVKUS inizializzato",
            "user_id": request.user_id,
            "stats": stats,
            "gemini_available": ai.gemini.available,
            "api_keys_configured": user_data.get("api_keys_configured", False)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Errore init: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        
@app.post("/api/chat")
async def chat_with_ai(request: ChatRequest):
    """Chat con MAVKUS"""
    try:
        # 🔍 LOG DI DEBUG
        logger.info(f"📥 Richiesta ricevuta:")
        logger.info(f"  - user_id: {request.user_id} (type: {type(request.user_id)})")
        logger.info(f"  - message: {request.message[:50]}...")
        logger.info(f"  - enable_critique: {request.enable_critique}")
        
        # Verifica input
        if not request.message.strip():
            raise HTTPException(status_code=400, detail="Messaggio vuoto")
        
        # Ottieni istanza AI
        ai = _create_ai_instance(request.user_id)
        
        logger.info(f"💬 Chat da {request.user_id[:8]}: {request.message[:50]}...")
        
        # Processa messaggio
        response, metadata = ai.chat(
            request.message,
            enable_critique=request.enable_critique
        )
        
        # Salva conversazione su Firebase
        conversation_data = {
            "title": request.message[:50] + ("..." if len(request.message) > 50 else ""),
            "messages": [
                {
                    "role": "user",
                    "content": request.message,
                    "timestamp": datetime.now().isoformat()
                },
                {
                    "role": "assistant",
                    "content": response,
                    "timestamp": datetime.now().isoformat(),
                    "metadata": metadata
                }
            ],
            "user_id": request.user_id,
            "message_count": 2
        }
        
        conversation_id = firebase_service.save_conversation(request.user_id, conversation_data)
        
        # Risposta
        return {
            "success": True,
            "response": response,
            "user_id": request.user_id,
            "conversation_id": conversation_id,
            "metadata": {
                "routed_to_gemini": metadata.get("routed_to_gemini", False),
                "gemini_used": metadata.get("gemini_used", False),
                "has_critique": bool(metadata.get("critique"))
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Errore chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))
@app.get("/api/conversations/{user_id}")
async def get_user_conversations(user_id: str, limit: int = 20):
    """Ottieni conversazioni utente"""
    try:
        conversations = firebase_service.get_conversations(user_id, limit)
        
        return {
            "success": True,
            "user_id": user_id,
            "conversations": conversations,
            "count": len(conversations)
        }
        
    except Exception as e:
        logger.error(f"❌ Errore get-conversations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/conversations/{user_id}/{conversation_id}")
async def delete_conversation(user_id: str, conversation_id: str):
    """Elimina conversazione"""
    try:
        success = firebase_service.delete_conversation(user_id, conversation_id)
        
        if success:
            return {
                "success": True,
                "message": "Conversazione eliminata",
                "user_id": user_id,
                "conversation_id": conversation_id
            }
        else:
            raise HTTPException(status_code=500, detail="Errore eliminazione")
            
    except Exception as e:
        logger.error(f"❌ Errore delete-conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stats/{user_id}")
async def get_user_stats(user_id: str):
    """Ottieni statistiche utente"""
    try:
        # Ottieni dati da Firebase
        user_data = firebase_service.get_user(user_id)
        
        if not user_data:
            raise HTTPException(status_code=404, detail="Utente non trovato")
        
        # Ottieni istanza AI per stats aggiuntive
        try:
            ai = _create_ai_instance(user_id)
            ai_stats = ai.get_stats()
        except:
            ai_stats = {}
        
        return {
            "success": True,
            "user_id": user_id,
            "firebase_data": {
                "total_conversations": user_data.get("total_conversations", 0),
                "total_tokens_used": user_data.get("total_tokens_used", 0),
                "created_at": user_data.get("created_at"),
                "last_login": user_data.get("last_login"),
                "api_keys_configured": user_data.get("api_keys_configured", False)
            },
            "ai_stats": ai_stats,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Errore stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
