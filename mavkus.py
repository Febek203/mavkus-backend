"""
MAVKUS AI - CORE ENGINE
"""
import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
from dotenv import load_dotenv

# Configurazione
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import LangChain
try:
    from langchain_groq import ChatGroq
    from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
    from langchain_core.chat_history import InMemoryChatMessageHistory
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    logger.error("❌ LangChain non disponibile")

# Import Gemini
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logger.warning("⚠️ Gemini non disponibile")

# =========================
# GEMINI SPECIALIST
# =========================
class GeminiSpecialist:
    """Specialista Gemini per Scienze"""
    
    def __init__(self, api_key: str = None):
        self.name = "Gemini Pro"
        self.specialty = "Scienze (Fisica, Chimica, Biologia), Matematica, Ricerca"
        self.consultations = 0
        self.successes = 0
        self.available = False
        
        if GEMINI_AVAILABLE and api_key:
            try:
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel('gemini-pro')
                self.available = True
                logger.info(f"✅ {self.name} attivo")
            except Exception as e:
                logger.error(f"❌ Errore inizializzazione Gemini: {e}")
                self.model = None
        else:
            self.model = None
    
    def consult(self, question: str, context: str = "") -> Dict[str, Any]:
        """Consulta Gemini"""
        if not self.available or not self.model:
            return {
                "answer": "❌ Gemini non disponibile",
                "success": False,
                "ai_name": self.name
            }
        
        self.consultations += 1
        
        try:
            prompt = f"""CONTESTO UTENTE: {context}

DOMANDA: {question}

Sei un esperto in {self.specialty}. Rispondi in modo dettagliato, scientifico ma comprensibile."""
            
            response = self.model.generate_content(prompt)
            answer = response.text if hasattr(response, 'text') else str(response)
            
            self.successes += 1
            return {
                "answer": answer,
                "ai_name": self.name,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"❌ Errore consulto Gemini: {e}")
            return {
                "answer": f"❌ Errore Gemini: {str(e)[:100]}",
                "success": False,
                "ai_name": self.name
            }
    
    def get_stats(self) -> Dict[str, Any]:
        """Ottieni statistiche"""
        success_rate = (self.successes / self.consultations * 100) if self.consultations > 0 else 0
        return {
            "name": self.name,
            "specialty": self.specialty,
            "consultations": self.consultations,
            "successes": self.successes,
            "success_rate": f"{success_rate:.1f}%",
            "available": self.available
        }

# =========================
# MAVKUS AI CORE
# =========================
class MavkusAI:
    """AI con routing intelligente e auto-valutazione"""
    
    def __init__(
        self,
        user_id: str,
        groq_api_key: str = None,
        gemini_api_key: str = None,
        model_name: str = "llama-3.3-70b-versatile",
        temperature: float = 0.7
    ):
        self.user_id = user_id
        self.save_file = f"user_memories/mavkus_memory_{user_id}.json"
        
        # Crea directory se non esiste
        os.makedirs("user_memories", exist_ok=True)
        
        # Inizializza Groq
        groq_key = groq_api_key or os.getenv("GROQ_API_KEY")
        if not groq_key:
            raise ValueError("GROQ_API_KEY mancante")
        
        try:
            self.model = ChatGroq(
                model=model_name,
                temperature=temperature,
                api_key=groq_key,
                max_tokens=4096
            )
            
            self.critic_model = ChatGroq(
                model=model_name,
                temperature=0.3,
                api_key=groq_key,
                max_tokens=1024
            )
            
            logger.info(f"🧠 Modello Groq inizializzato: {model_name}")
        except Exception as e:
            logger.error(f"❌ Errore inizializzazione Groq: {e}")
            raise
        
        # Inizializza Gemini
        self.gemini = GeminiSpecialist(gemini_api_key)
        
        # Inizializza memoria
        self.chat_history = InMemoryChatMessageHistory()
        self.user_profile = self._init_user_profile()
        self.learned_patterns = self._init_learned_patterns()
        self.routing_stats = self._init_routing_stats()
        
        # Carica memoria esistente
        self.load_memory()
        
        logger.info(f"🚀 MAVKUS AI inizializzato per utente: {user_id[:8]}...")
    
    def _init_user_profile(self) -> Dict[str, Any]:
        """Inizializza profilo utente"""
        return {
            "style": "neutral",
            "topics_of_interest": [],
            "conversation_count": 0,
            "preferred_response_length": "medium",
            "language_level": "medium",
            "quality_metrics": {
                "avg_response_score": 0.0,
                "improvement_trend": [],
                "weak_areas": [],
                "strong_areas": []
            }
        }
    
    def _init_learned_patterns(self) -> Dict[str, Any]:
        """Inizializza pattern appresi"""
        return {
            "successful_responses": [],
            "failed_responses": [],
            "improvement_strategies": [],
            "gemini_consultations": []
        }
    
    def _init_routing_stats(self) -> Dict[str, Any]:
        """Inizializza statistiche routing"""
        return {
            "total_questions": 0,
            "routed_to_gemini": 0,
            "handled_by_coordinator": 0,
            "gemini_success_rate": 0
        }
    
    # ---------- SISTEMA PROMPT ----------
    def _get_system_prompt(self) -> str:
        """Genera prompt di sistema"""
        return f"""Sei MAVKUS, un'AI intelligente con accesso a uno specialista scientifico.

PROFILO UTENTE:
{json.dumps(self.user_profile, ensure_ascii=False, indent=2)}

SPECIALISTA DISPONIBILE:
- Gemini Pro: {self.gemini.specialty}

STATISTICHE ROUTING:
- Domande totali: {self.routing_stats['total_questions']}
- Inviate a Gemini: {self.routing_stats['routed_to_gemini']}
- Successo Gemini: {self.routing_stats['gemini_success_rate']:.1f}%

ISTRUZIONI:
1. Adatta il tono allo stile dell'utente ({self.user_profile['style']})
2. Se la domanda riguarda SCIENZE o MATEMATICA, consulta lo specialista
3. Per coding e conversazione, rispondi direttamente
4. Sii chiaro, utile e conciso"""
    
    # ---------- ANALISI UTENTE ----------
    def analyze_user_message(self, message: str):
        """Analizza stile e interessi utente"""
        message_lower = message.lower()
        
        # Analizza stile
        if "gentilmente" in message_lower or "per favore" in message_lower:
            self.user_profile["style"] = "formal"
        elif "ciao" in message_lower or "hey" in message_lower:
            self.user_profile["style"] = "casual"
        elif "funzione" in message_lower or "codice" in message_lower:
            self.user_profile["style"] = "technical"
        else:
            self.user_profile["style"] = "neutral"
        
        # Rileva interessi
        science_keywords = ["fisica", "chimica", "biologia", "matematica", "scienza"]
        coding_keywords = ["python", "javascript", "programmazione", "codice", "algoritmo"]
        
        for keyword in science_keywords + coding_keywords:
            if keyword in message_lower and keyword not in self.user_profile["topics_of_interest"]:
                self.user_profile["topics_of_interest"].append(keyword)
        
        # Limita lista interessi
        if len(self.user_profile["topics_of_interest"]) > 10:
            self.user_profile["topics_of_interest"] = self.user_profile["topics_of_interest"][-10:]
    
    # ---------- ROUTING INTELLIGENTE ----------
    def should_route_to_gemini(self, question: str) -> bool:
        """Decide se inviare a Gemini"""
        science_keywords = [
            "fisica", "chimica", "biologia", "matematica",
            "atomo", "molecola", "cellula", "equazione",
            "teorema", "energia", "forza", "gravità",
            "relatività", "quantistica", "organico"
        ]
        
        question_lower = question.lower()
        science_count = sum(1 for kw in science_keywords if kw in question_lower)
        
        return science_count >= 2 or any(kw in question_lower for kw in ["fisica", "chimica", "biologia"])
    
    # ---------- CHAT ----------
    def chat(self, user_message: str, enable_critique: bool = True) -> Tuple[str, Dict[str, Any]]:
        """Elabora un messaggio utente"""
        # Analizza utente
        self.analyze_user_message(user_message)
        self.user_profile["conversation_count"] += 1
        self.routing_stats["total_questions"] += 1
        
        # Aggiungi a cronologia
        self.chat_history.add_user_message(user_message)
        
        # Routing decision
        route_to_gemini = self.should_route_to_gemini(user_message)
        gemini_response = None
        
        if route_to_gemini and self.gemini.available:
            logger.info("🔬 Domanda scientifica → Consulto Gemini")
            self.routing_stats["routed_to_gemini"] += 1
            
            # Consulta Gemini
            context = f"Stile: {self.user_profile['style']}"
            gemini_response = self.gemini.consult(user_message, context)
            
            if gemini_response["success"]:
                self.learned_patterns["gemini_consultations"].append({
                    "timestamp": datetime.now().isoformat(),
                    "question": user_message[:100],
                    "success": True
                })
        else:
            self.routing_stats["handled_by_coordinator"] += 1
        
        # Prepara messaggi per Groq
        messages = [SystemMessage(content=self._get_system_prompt())]
        
        # Aggiungi risposta Gemini se disponibile
        if gemini_response and gemini_response["success"]:
            messages.append(SystemMessage(
                content=f"CONSULENZA SCIENTIFICA da Gemini:\n\n{gemini_response['answer']}\n\nUsa queste informazioni per rispondere all'utente."
            ))
        
        # Aggiungi cronologia
        messages.extend(self.chat_history.messages[-10:])  # Ultimi 10 messaggi
        
        # Genera risposta
        try:
            response = self.model.invoke(messages)
            ai_response = response.content
            self.chat_history.add_ai_message(ai_response)
        except Exception as e:
            ai_response = f"❌ Errore generazione risposta: {str(e)}"
            self.chat_history.add_ai_message(ai_response)
        
        # Auto-valutazione
        critique = {}
        if enable_critique:
            critique = self._critique_response(user_message, ai_response)
            self._learn_from_critique(critique)
        
        # Salva periodicamente
        if self.user_profile["conversation_count"] % 5 == 0:
            self.save_memory()
        
        # Metadata
        metadata = {
            "routed_to_gemini": route_to_gemini,
            "gemini_used": gemini_response["success"] if gemini_response else False,
            "gemini_response": gemini_response if gemini_response else None,
            "critique": critique
        }
        
        return ai_response, metadata
    
    # ---------- AUTO-VALUTAZIONE ----------
    def _critique_response(self, user_message: str, ai_response: str) -> Dict[str, Any]:
        """Valuta la risposta generata"""
        try:
            prompt = f"""Valuta questa risposta AI (1-10):

DOMANDA: {user_message}
RISPOSTA: {ai_response}

Criteri:
- Rilevanza alla domanda
- Chiarezza espositiva
- Completezza informativa
- Accuratezza scientifica
- Utilità pratica

Rispondi in formato JSON:"""
            
            critic_response = self.critic_model.invoke([
                SystemMessage(content="Sei un critico obiettivo e preciso."),
                HumanMessage(content=prompt)
            ])
            
            # Estrai JSON dalla risposta
            content = critic_response.content.strip()
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0].strip()
            else:
                json_str = content
            
            critique = json.loads(json_str)
            return critique
            
        except Exception as e:
            logger.error(f"❌ Errore auto-valutazione: {e}")
            return {
                "scores": {"rilevanza": 7, "chiarezza": 7, "completezza": 7, "accuratezza": 7, "utilita": 7},
                "overall_score": 7.0,
                "strengths": ["Risposta generica"],
                "weaknesses": ["Valutazione non disponibile"],
                "improvement_suggestion": "Continua a migliorare",
                "category": "generale"
            }
    
    def _learn_from_critique(self, critique: Dict[str, Any]):
        """Apprende dalla critica"""
        score = critique.get("overall_score", 7.0)
        
        # Aggiorna score medio
        metrics = self.user_profile["quality_metrics"]
        count = self.user_profile["conversation_count"]
        current_avg = metrics["avg_response_score"]
        metrics["avg_response_score"] = (current_avg * (count - 1) + score) / count
        
        # Aggiorna trend
        metrics["improvement_trend"].append(score)
        if len(metrics["improvement_trend"]) > 20:
            metrics["improvement_trend"] = metrics["improvement_trend"][-20:]
        
        # Identifica aree forti/deboli
        for area, value in critique.get("scores", {}).items():
            if value >= 8 and area not in metrics["strong_areas"]:
                metrics["strong_areas"].append(area)
            elif value <= 5 and area not in metrics["weak_areas"]:
                metrics["weak_areas"].append(area)
        
        # Limita liste
        if len(metrics["strong_areas"]) > 5:
            metrics["strong_areas"] = metrics["strong_areas"][-5:]
        if len(metrics["weak_areas"]) > 5:
            metrics["weak_areas"] = metrics["weak_areas"][-5:]
    
    # ---------- GESTIONE MEMORIA ----------
    def save_memory(self):
        """Salva memoria su file"""
        try:
            data = {
                "user_id": self.user_id,
                "user_profile": self.user_profile,
                "learned_patterns": self.learned_patterns,
                "routing_stats": self.routing_stats,
                "gemini_stats": self.gemini.get_stats(),
                "chat_history": [
                    {
                        "role": "human" if isinstance(msg, HumanMessage) else "ai",
                        "content": msg.content,
                        "timestamp": datetime.now().isoformat()
                    }
                    for msg in self.chat_history.messages[-50:]  # Ultimi 50 messaggi
                ],
                "last_saved": datetime.now().isoformat()
            }
            
            with open(self.save_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"💾 Memoria salvata: {self.save_file}")
            
        except Exception as e:
            logger.error(f"❌ Errore salvataggio memoria: {e}")
    
    def load_memory(self):
        """Carica memoria da file"""
        try:
            if not os.path.exists(self.save_file):
                logger.info("🆕 Nuova memoria creata")
                return
            
            with open(self.save_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Carica profilo utente
            self.user_profile = data.get("user_profile", self.user_profile)
            self.learned_patterns = data.get("learned_patterns", self.learned_patterns)
            self.routing_stats = data.get("routing_stats", self.routing_stats)
            
            # Ricostruisci cronologia
            self.chat_history.clear()
            for msg_data in data.get("chat_history", []):
                if msg_data["role"] == "human":
                    self.chat_history.add_user_message(msg_data["content"])
                else:
                    self.chat_history.add_ai_message(msg_data["content"])
            
            logger.info(f"✅ Memoria caricata: {len(data.get('chat_history', []))} messaggi")
            
        except Exception as e:
            logger.error(f"⚠️ Errore caricamento memoria: {e}")
    
    def clear_memory(self):
        """Cancella memoria"""
        self.chat_history.clear()
        self.user_profile = self._init_user_profile()
        self.learned_patterns = self._init_learned_patterns()
        self.routing_stats = self._init_routing_stats()
        
        if os.path.exists(self.save_file):
            os.remove(self.save_file)
        
        logger.info("🧹 Memoria azzerata")
    
    # ---------- UTILITY ----------
    def get_stats(self) -> Dict[str, Any]:
        """Ottieni statistiche complete"""
        return {
            "user_id": self.user_id,
            "user_profile": self.user_profile,
            "gemini": self.gemini.get_stats(),
            "routing": self.routing_stats,
            "conversation_count": self.user_profile["conversation_count"]
        }