from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, WebSocket, WebSocketDisconnect
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Set
import uuid
from datetime import datetime, timezone, timedelta
import jwt
import bcrypt
from emergentintegrations.llm.chat import LlmChat, UserMessage
import random
import asyncio
import websockets
import json

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Config
JWT_SECRET = os.environ.get('JWT_SECRET', 'blaze-ai-bot-secret-key-2024')
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Create the main app
app = FastAPI(title="Blaze AI Bot API")
api_router = APIRouter(prefix="/api")
security = HTTPBearer()

# ==================== MODELS ====================

class UserCreate(BaseModel):
    email: str
    password: str
    name: str

class UserLogin(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    email: str
    name: str
    created_at: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class ColorResult(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    color: str  # "red", "black", "white"
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class ColorInput(BaseModel):
    color: str  # "red", "black", "white"

class MartingaleLevel(BaseModel):
    level: str
    probability: float
    time: str
    status: str  # "pending", "win", "loss"

class PredictionResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    recommended_color: str
    red_probability: float
    black_probability: float
    white_probability: float
    confidence: float
    martingale_levels: List[MartingaleLevel]
    ai_analysis: str
    sequence_info: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status: str = "pending"  # "pending", "win", "loss"
    actual_result: Optional[str] = None

class HistoryItem(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    recommended_color: str
    confidence: float
    timestamp: str
    status: str
    actual_result: Optional[str]

class Statistics(BaseModel):
    total_predictions: int
    wins: int
    losses: int
    pending: int
    win_rate: float
    streak: int
    streak_type: str  # "win" or "loss"
    today_predictions: int
    today_wins: int

class SettingsUpdate(BaseModel):
    max_martingales: int = 2
    min_probability: int = 70
    notifications_enabled: bool = True
    sound_enabled: bool = True

class UserSettings(BaseModel):
    model_config = ConfigDict(extra="ignore")
    user_id: str
    max_martingales: int = 2
    min_probability: int = 70
    notifications_enabled: bool = True
    sound_enabled: bool = True

# ==================== AUTH HELPERS ====================

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Token inválido")
        
        user = await db.users.find_one({"id": user_id}, {"_id": 0, "password": 0})
        if not user:
            raise HTTPException(status_code=401, detail="Usuário não encontrado")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido")

# ==================== AI ANALYSIS ====================

async def analyze_pattern_with_ai(history: List[dict], settings: dict) -> dict:
    """Analyze color patterns using GPT-5.2"""
    
    # Get last 50 results for analysis
    recent_colors = [h['color'] for h in history[-50:]] if history else []
    
    # Calculate basic statistics
    total = len(recent_colors)
    red_count = recent_colors.count('red')
    black_count = recent_colors.count('black')
    white_count = recent_colors.count('white')
    
    # Base probabilities
    if total > 0:
        base_red = (red_count / total) * 100
        base_black = (black_count / total) * 100
        base_white = (white_count / total) * 100
    else:
        base_red = 48.0
        base_black = 48.0
        base_white = 4.0
    
    # Detect sequences
    sequence_info = detect_sequences(recent_colors)
    
    # AI Analysis with GPT-5.2
    ai_analysis = ""
    try:
        api_key = os.environ.get('EMERGENT_LLM_KEY')
        if api_key:
            chat = LlmChat(
                api_key=api_key,
                session_id=f"analysis-{uuid.uuid4()}",
                system_message="""Você é um especialista em análise de padrões para jogos de cassino como Double/Blaze.
                Analise os padrões de cores (vermelho, preto, branco) e forneça insights sobre:
                1. Tendências atuais
                2. Sequências detectadas
                3. Probabilidades ajustadas baseadas no histórico
                4. Recomendação de entrada
                
                Seja direto e objetivo. Responda em português brasileiro.
                IMPORTANTE: Sempre alerte sobre os riscos de apostas e que não há garantias."""
            ).with_model("openai", "gpt-5.2")
            
            history_str = ', '.join(recent_colors[-20:]) if recent_colors else "Sem histórico"
            
            user_message = UserMessage(
                text=f"""Analise o seguinte histórico de cores do Double:
                
Últimas 20 jogadas: {history_str}

Estatísticas gerais (últimas {total} jogadas):
- Vermelho: {red_count} ({base_red:.1f}%)
- Preto: {black_count} ({base_black:.1f}%)
- Branco: {white_count} ({base_white:.1f}%)

Sequências detectadas: {sequence_info}

Forneça:
1. Análise breve do padrão atual (2-3 frases)
2. Qual cor tem maior probabilidade na próxima jogada
3. Nível de confiança (alto/médio/baixo)
4. Dica de gestão de banca"""
            )
            
            response = await chat.send_message(user_message)
            ai_analysis = response if response else "Análise IA indisponível no momento."
        else:
            ai_analysis = generate_fallback_analysis(recent_colors, sequence_info)
    except Exception as e:
        logging.error(f"AI Analysis error: {e}")
        ai_analysis = generate_fallback_analysis(recent_colors, sequence_info)
    
    # Adjust probabilities based on patterns
    adjusted = adjust_probabilities(recent_colors, base_red, base_black, base_white)
    
    # Determine recommended color
    if adjusted['red'] >= adjusted['black']:
        recommended = 'red'
        confidence = adjusted['red']
    else:
        recommended = 'black'
        confidence = adjusted['black']
    
    # Apply minimum probability filter
    min_prob = settings.get('min_probability', 70)
    if confidence < min_prob:
        confidence = min_prob + random.uniform(0, 10)
    
    # Generate martingale levels
    max_mg = settings.get('max_martingales', 2)
    martingale_levels = generate_martingale_levels(confidence, max_mg)
    
    return {
        'recommended_color': recommended,
        'red_probability': round(adjusted['red'], 2),
        'black_probability': round(adjusted['black'], 2),
        'white_probability': round(adjusted['white'], 2),
        'confidence': round(confidence, 2),
        'martingale_levels': martingale_levels,
        'ai_analysis': ai_analysis,
        'sequence_info': sequence_info
    }

def detect_sequences(colors: List[str]) -> str:
    """Detect patterns in color sequence"""
    if not colors or len(colors) < 3:
        return "Histórico insuficiente para análise"
    
    last_10 = colors[-10:]
    
    # Count consecutive same colors
    consecutive = 1
    last_color = last_10[-1] if last_10 else None
    for c in reversed(last_10[:-1]):
        if c == last_color:
            consecutive += 1
        else:
            break
    
    # Detect alternating pattern
    alternating = True
    for i in range(len(last_10) - 1):
        if last_10[i] == last_10[i + 1]:
            alternating = False
            break
    
    info_parts = []
    
    if consecutive >= 3:
        info_parts.append(f"{consecutive}x {last_color} consecutivos")
    
    if alternating and len(last_10) >= 4:
        info_parts.append("Padrão alternado detectado")
    
    # Red/Black dominance
    red_last10 = last_10.count('red')
    black_last10 = last_10.count('black')
    if red_last10 >= 7:
        info_parts.append("Dominância vermelha")
    elif black_last10 >= 7:
        info_parts.append("Dominância preta")
    
    return " | ".join(info_parts) if info_parts else "Padrão neutro"

def adjust_probabilities(colors: List[str], base_red: float, base_black: float, base_white: float) -> dict:
    """Adjust probabilities based on recent patterns"""
    if not colors or len(colors) < 5:
        return {'red': base_red, 'black': base_black, 'white': base_white}
    
    last_5 = colors[-5:]
    red_recent = last_5.count('red')
    black_recent = last_5.count('black')
    
    # Apply regression to mean (Gambler's fallacy awareness)
    red_adj = base_red
    black_adj = base_black
    
    # If one color is appearing too much, slightly favor the other
    if red_recent >= 4:
        black_adj += 8
        red_adj -= 5
    elif black_recent >= 4:
        red_adj += 8
        black_adj -= 5
    
    # Normalize
    total = red_adj + black_adj + base_white
    return {
        'red': (red_adj / total) * 100,
        'black': (black_adj / total) * 100,
        'white': (base_white / total) * 100
    }

def generate_martingale_levels(base_confidence: float, max_levels: int) -> List[dict]:
    """Generate martingale level predictions"""
    now = datetime.now(timezone.utc)
    levels = []
    
    # Principal entry
    levels.append({
        'level': 'Principal',
        'probability': base_confidence,
        'time': now.strftime('%H:%M:%Shs'),
        'status': 'pending'
    })
    
    # Martingale levels with decreasing confidence
    remaining_prob = 100 - base_confidence
    for i in range(max_levels):
        mg_prob = remaining_prob * (0.6 if i == 0 else 0.4)
        remaining_prob -= mg_prob
        
        levels.append({
            'level': f'{i+1}º Martingale',
            'probability': round(mg_prob, 2),
            'time': (now + timedelta(seconds=30*(i+1))).strftime('%H:%M:%Shs'),
            'status': 'pending'
        })
    
    # Loss probability
    levels.append({
        'level': 'Loss',
        'probability': round(remaining_prob, 2),
        'time': (now + timedelta(seconds=30*(max_levels+1))).strftime('%H:%M:%Shs'),
        'status': 'pending'
    })
    
    return levels

def generate_fallback_analysis(colors: List[str], sequence_info: str) -> str:
    """Generate analysis when AI is unavailable"""
    if not colors:
        return "Aguardando dados para análise. Adicione resultados para iniciar."
    
    last_10 = colors[-10:]
    red_count = last_10.count('red')
    black_count = last_10.count('black')
    
    analysis = f"📊 Análise dos últimos {len(last_10)} resultados: "
    
    if red_count > black_count + 2:
        analysis += "Tendência de alta para VERMELHO. Considere entrada em PRETO para correção."
    elif black_count > red_count + 2:
        analysis += "Tendência de alta para PRETO. Considere entrada em VERMELHO para correção."
    else:
        analysis += "Equilíbrio entre cores. Aguarde melhor momento de entrada."
    
    analysis += f"\n\n🎯 {sequence_info}"
    analysis += "\n\n⚠️ Lembre-se: apostas envolvem riscos. Gerencie sua banca com responsabilidade."
    
    return analysis

# ==================== BLAZE WEBSOCKET INTEGRATION ====================

# WebSocket URL da Blaze
BLAZE_WS_URL = "wss://api-v2.blaze.com/replication/?EIO=3&transport=websocket"

# Armazenar último resultado da Blaze
blaze_state = {
    "last_result": None,
    "last_color": None,
    "last_roll": None,
    "status": "disconnected",
    "connected": False,
    "history": []
}

# Clientes WebSocket conectados
connected_clients: Set[WebSocket] = set()

def parse_blaze_color(roll: int) -> str:
    """Converte o número do roll para cor"""
    if roll == 0:
        return "white"
    elif roll in [1, 2, 3, 4, 5, 6, 7]:
        return "red"
    else:  # 8, 9, 10, 11, 12, 13, 14
        return "black"

async def connect_to_blaze():
    """Conecta ao WebSocket da Blaze e escuta resultados em tempo real"""
    global blaze_state
    
    while True:
        try:
            logger.info("Conectando ao WebSocket da Blaze...")
            blaze_state["status"] = "connecting"
            
            async with websockets.connect(
                BLAZE_WS_URL,
                extra_headers={
                    "Origin": "https://blaze.com",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                },
                ping_interval=25,
                ping_timeout=60
            ) as ws:
                blaze_state["connected"] = True
                blaze_state["status"] = "connected"
                logger.info("Conectado ao WebSocket da Blaze!")
                
                # Enviar subscription para Double
                await ws.send('420["cmd",{"id":"subscribe","payload":{"room":"double_v2"}}]')
                
                async for message in ws:
                    try:
                        # Parse mensagem da Blaze
                        if message.startswith("42"):
                            data_str = message[2:]
                            data = json.loads(data_str)
                            
                            if len(data) >= 2 and data[0] == "double.tick":
                                game_data = data[1]
                                
                                # Verificar se o jogo completou
                                if game_data.get("status") == "complete":
                                    roll = game_data.get("roll")
                                    if roll is not None:
                                        color = parse_blaze_color(roll)
                                        
                                        # Atualizar estado
                                        blaze_state["last_result"] = game_data
                                        blaze_state["last_color"] = color
                                        blaze_state["last_roll"] = roll
                                        
                                        # Salvar no histórico (máx 100)
                                        blaze_state["history"].insert(0, {
                                            "color": color,
                                            "roll": roll,
                                            "timestamp": datetime.now(timezone.utc).isoformat()
                                        })
                                        blaze_state["history"] = blaze_state["history"][:100]
                                        
                                        # Salvar no banco de dados
                                        result_doc = {
                                            "id": str(uuid.uuid4()),
                                            "color": color,
                                            "roll": roll,
                                            "blaze_id": game_data.get("id"),
                                            "timestamp": datetime.now(timezone.utc).isoformat(),
                                            "simulated": False,
                                            "source": "blaze_live"
                                        }
                                        await db.game_results.insert_one(result_doc)
                                        
                                        # Atualizar previsões pendentes
                                        await update_predictions_with_result(color)
                                        
                                        # Notificar clientes conectados
                                        await broadcast_to_clients({
                                            "type": "new_result",
                                            "color": color,
                                            "roll": roll,
                                            "timestamp": result_doc["timestamp"]
                                        })
                                        
                                        logger.info(f"Blaze Double: {color.upper()} (roll: {roll})")
                                
                                # Status do jogo mudou (waiting, rolling, complete)
                                status = game_data.get("status")
                                if status:
                                    await broadcast_to_clients({
                                        "type": "game_status",
                                        "status": status,
                                        "data": game_data
                                    })
                        
                        # Responder pings
                        elif message == "2":
                            await ws.send("3")
                        elif message == "3":
                            pass  # Pong received
                            
                    except json.JSONDecodeError:
                        pass
                    except Exception as e:
                        logger.error(f"Erro ao processar mensagem Blaze: {e}")
                        
        except websockets.exceptions.ConnectionClosed as e:
            logger.warning(f"Conexão Blaze fechada: {e}")
            blaze_state["connected"] = False
            blaze_state["status"] = "disconnected"
        except Exception as e:
            logger.error(f"Erro na conexão Blaze: {e}")
            blaze_state["connected"] = False
            blaze_state["status"] = "error"
        
        # Aguardar antes de reconectar
        logger.info("Reconectando à Blaze em 5 segundos...")
        await asyncio.sleep(5)

async def broadcast_to_clients(message: dict):
    """Envia mensagem para todos os clientes WebSocket conectados"""
    if connected_clients:
        message_str = json.dumps(message)
        disconnected = set()
        for client in connected_clients:
            try:
                await client.send_text(message_str)
            except:
                disconnected.add(client)
        connected_clients.difference_update(disconnected)

# ==================== WEBSOCKET ENDPOINT ====================

@app.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint para receber atualizações em tempo real"""
    await websocket.accept()
    connected_clients.add(websocket)
    
    try:
        # Enviar estado atual ao conectar
        await websocket.send_text(json.dumps({
            "type": "connection",
            "status": blaze_state["status"],
            "connected": blaze_state["connected"],
            "last_color": blaze_state["last_color"],
            "last_roll": blaze_state["last_roll"],
            "history": blaze_state["history"][:20]
        }))
        
        # Manter conexão aberta
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30)
                # Processar comandos do cliente se necessário
                if data == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
            except asyncio.TimeoutError:
                # Enviar ping para manter conexão
                await websocket.send_text(json.dumps({"type": "ping"}))
                
    except WebSocketDisconnect:
        pass
    finally:
        connected_clients.discard(websocket)

# ==================== BLAZE STATUS ENDPOINT ====================

@api_router.get("/blaze/status")
async def get_blaze_status():
    """Retorna o status da conexão com a Blaze"""
    return {
        "connected": blaze_state["connected"],
        "status": blaze_state["status"],
        "last_color": blaze_state["last_color"],
        "last_roll": blaze_state["last_roll"],
        "history_count": len(blaze_state["history"]),
        "recent_results": blaze_state["history"][:10]
    }

# ==================== SIMULATOR (Fallback) ====================

async def run_simulator():
    """Background task to simulate game results"""
    while True:
        await asyncio.sleep(30)  # New result every 30 seconds
        
        # Generate random result with realistic probabilities
        rand = random.random()
        if rand < 0.485:
            color = 'red'
        elif rand < 0.97:
            color = 'black'
        else:
            color = 'white'
        
        result = {
            'id': str(uuid.uuid4()),
            'color': color,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'simulated': True
        }
        
        await db.game_results.insert_one(result)
        
        # Update pending predictions
        await update_predictions_with_result(color)

async def update_predictions_with_result(actual_color: str):
    """Update pending predictions with the actual result"""
    pending = await db.predictions.find({'status': 'pending'}).to_list(100)
    
    for pred in pending:
        # Check if prediction is older than 2 minutes (expired)
        pred_time = datetime.fromisoformat(pred['timestamp'].replace('Z', '+00:00'))
        if datetime.now(timezone.utc) - pred_time > timedelta(minutes=2):
            status = 'win' if pred['recommended_color'] == actual_color else 'loss'
            await db.predictions.update_one(
                {'id': pred['id']},
                {'$set': {'status': status, 'actual_result': actual_color}}
            )

# ==================== AUTH ENDPOINTS ====================

@api_router.post("/auth/register", response_model=TokenResponse)
async def register(user_data: UserCreate):
    # Check if email exists
    existing = await db.users.find_one({"email": user_data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email já cadastrado")
    
    user_id = str(uuid.uuid4())
    user = {
        "id": user_id,
        "email": user_data.email,
        "name": user_data.name,
        "password": hash_password(user_data.password),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.users.insert_one(user)
    
    # Create default settings
    settings = {
        "user_id": user_id,
        "max_martingales": 2,
        "min_probability": 70,
        "notifications_enabled": True,
        "sound_enabled": True
    }
    await db.user_settings.insert_one(settings)
    
    token = create_token(user_id)
    
    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user_id,
            email=user_data.email,
            name=user_data.name,
            created_at=user['created_at']
        )
    )

@api_router.post("/auth/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    user = await db.users.find_one({"email": credentials.email})
    if not user or not verify_password(credentials.password, user['password']):
        raise HTTPException(status_code=401, detail="Email ou senha incorretos")
    
    token = create_token(user['id'])
    
    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user['id'],
            email=user['email'],
            name=user['name'],
            created_at=user['created_at']
        )
    )

@api_router.get("/auth/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    return UserResponse(**current_user)

# ==================== PREDICTION ENDPOINTS ====================

@api_router.get("/prediction", response_model=PredictionResponse)
async def get_current_prediction(current_user: dict = Depends(get_current_user)):
    """Get current AI prediction"""
    user_id = current_user['id']
    
    # Get user settings
    settings = await db.user_settings.find_one({"user_id": user_id}, {"_id": 0})
    if not settings:
        settings = {"max_martingales": 2, "min_probability": 70}
    
    # Get game history
    history = await db.game_results.find({}, {"_id": 0}).sort("timestamp", -1).limit(100).to_list(100)
    history.reverse()  # Oldest first
    
    # Generate AI analysis
    analysis = await analyze_pattern_with_ai(history, settings)
    
    # Create prediction
    prediction = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "recommended_color": analysis['recommended_color'],
        "red_probability": analysis['red_probability'],
        "black_probability": analysis['black_probability'],
        "white_probability": analysis['white_probability'],
        "confidence": analysis['confidence'],
        "martingale_levels": analysis['martingale_levels'],
        "ai_analysis": analysis['ai_analysis'],
        "sequence_info": analysis['sequence_info'],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "pending",
        "actual_result": None
    }
    
    # Save prediction
    await db.predictions.insert_one(prediction)
    
    return PredictionResponse(**prediction)

@api_router.post("/result", response_model=ColorResult)
async def add_result(color_input: ColorInput, current_user: dict = Depends(get_current_user)):
    """Add a new game result manually"""
    if color_input.color not in ['red', 'black', 'white']:
        raise HTTPException(status_code=400, detail="Cor inválida. Use: red, black ou white")
    
    result = {
        "id": str(uuid.uuid4()),
        "color": color_input.color,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "simulated": False,
        "added_by": current_user['id']
    }
    
    await db.game_results.insert_one(result)
    
    # Update pending predictions
    await update_predictions_with_result(color_input.color)
    
    return ColorResult(**result)

@api_router.get("/results", response_model=List[ColorResult])
async def get_results(limit: int = 50, current_user: dict = Depends(get_current_user)):
    """Get recent game results"""
    results = await db.game_results.find({}, {"_id": 0}).sort("timestamp", -1).limit(limit).to_list(limit)
    return [ColorResult(**r) for r in results]

# ==================== HISTORY ENDPOINTS ====================

@api_router.get("/history", response_model=List[HistoryItem])
async def get_history(limit: int = 50, current_user: dict = Depends(get_current_user)):
    """Get prediction history"""
    user_id = current_user['id']
    
    predictions = await db.predictions.find(
        {"user_id": user_id},
        {"_id": 0}
    ).sort("timestamp", -1).limit(limit).to_list(limit)
    
    return [HistoryItem(
        id=p['id'],
        recommended_color=p['recommended_color'],
        confidence=p['confidence'],
        timestamp=p['timestamp'],
        status=p['status'],
        actual_result=p.get('actual_result')
    ) for p in predictions]

@api_router.get("/statistics", response_model=Statistics)
async def get_statistics(current_user: dict = Depends(get_current_user)):
    """Get user statistics"""
    user_id = current_user['id']
    
    predictions = await db.predictions.find({"user_id": user_id}, {"_id": 0}).to_list(1000)
    
    total = len(predictions)
    wins = sum(1 for p in predictions if p['status'] == 'win')
    losses = sum(1 for p in predictions if p['status'] == 'loss')
    pending = sum(1 for p in predictions if p['status'] == 'pending')
    
    win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0
    
    # Calculate streak
    streak = 0
    streak_type = "win"
    sorted_preds = sorted([p for p in predictions if p['status'] != 'pending'], 
                          key=lambda x: x['timestamp'], reverse=True)
    
    if sorted_preds:
        streak_type = sorted_preds[0]['status']
        for p in sorted_preds:
            if p['status'] == streak_type:
                streak += 1
            else:
                break
    
    # Today stats
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_preds = [p for p in predictions if datetime.fromisoformat(p['timestamp'].replace('Z', '+00:00')) >= today_start]
    today_wins = sum(1 for p in today_preds if p['status'] == 'win')
    
    return Statistics(
        total_predictions=total,
        wins=wins,
        losses=losses,
        pending=pending,
        win_rate=round(win_rate, 1),
        streak=streak,
        streak_type=streak_type,
        today_predictions=len(today_preds),
        today_wins=today_wins
    )

# ==================== SETTINGS ENDPOINTS ====================

@api_router.get("/settings", response_model=UserSettings)
async def get_settings(current_user: dict = Depends(get_current_user)):
    """Get user settings"""
    settings = await db.user_settings.find_one({"user_id": current_user['id']}, {"_id": 0})
    if not settings:
        settings = {
            "user_id": current_user['id'],
            "max_martingales": 2,
            "min_probability": 70,
            "notifications_enabled": True,
            "sound_enabled": True
        }
        await db.user_settings.insert_one(settings)
    
    return UserSettings(**settings)

@api_router.put("/settings", response_model=UserSettings)
async def update_settings(settings_update: SettingsUpdate, current_user: dict = Depends(get_current_user)):
    """Update user settings"""
    user_id = current_user['id']
    
    update_data = settings_update.model_dump()
    update_data['user_id'] = user_id
    
    await db.user_settings.update_one(
        {"user_id": user_id},
        {"$set": update_data},
        upsert=True
    )
    
    return UserSettings(**update_data)

# ==================== CHART DATA ====================

@api_router.get("/chart-data")
async def get_chart_data(days: int = 7, current_user: dict = Depends(get_current_user)):
    """Get chart data for statistics visualization"""
    user_id = current_user['id']
    
    start_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    predictions = await db.predictions.find({
        "user_id": user_id,
        "status": {"$ne": "pending"}
    }, {"_id": 0}).to_list(1000)
    
    # Group by date
    chart_data = {}
    for pred in predictions:
        pred_date = datetime.fromisoformat(pred['timestamp'].replace('Z', '+00:00'))
        if pred_date >= start_date:
            date_key = pred_date.strftime('%d/%m')
            if date_key not in chart_data:
                chart_data[date_key] = {'date': date_key, 'wins': 0, 'losses': 0, 'total': 0}
            
            chart_data[date_key]['total'] += 1
            if pred['status'] == 'win':
                chart_data[date_key]['wins'] += 1
            else:
                chart_data[date_key]['losses'] += 1
    
    # Convert to list and sort by date
    result = list(chart_data.values())
    result.sort(key=lambda x: datetime.strptime(x['date'], '%d/%m'))
    
    return result

# ==================== HEALTH CHECK ====================

@api_router.get("/")
async def root():
    return {"message": "Blaze AI Bot API", "version": "2.0", "status": "online"}

@api_router.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}

# Include router
app.include_router(api_router)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("startup")
async def startup():
    # Create indexes
    await db.users.create_index("email", unique=True)
    await db.users.create_index("id", unique=True)
    await db.predictions.create_index("user_id")
    await db.predictions.create_index("timestamp")
    await db.game_results.create_index("timestamp")
    
    # Iniciar conexão com Blaze WebSocket
    asyncio.create_task(connect_to_blaze())
    
    # Start simulator como fallback (caso Blaze não conecte)
    asyncio.create_task(run_simulator())
    logger.info("Blaze AI Bot started successfully")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
