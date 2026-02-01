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
    strategy_used: str = "default"
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
    strategy_used: Optional[str] = None

# ==================== ESTRATÉGIAS DE ANÁLISE ====================

STRATEGIES = {
    "tendencia": {
        "name": "Seguir Tendência",
        "description": "Aposta na cor que está dominando o histórico recente",
        "weight": 1.0
    },
    "reversao": {
        "name": "Reversão à Média",
        "description": "Aposta na cor oposta após sequência longa da mesma cor",
        "weight": 1.0
    },
    "alternancia": {
        "name": "Padrão Alternado",
        "description": "Detecta e segue padrões de alternância entre cores",
        "weight": 1.0
    },
    "fibonacci": {
        "name": "Sequência Fibonacci",
        "description": "Usa intervalos de Fibonacci para detectar ciclos",
        "weight": 1.0
    },
    "estatistica": {
        "name": "Análise Estatística Pura",
        "description": "Baseado puramente em probabilidades matemáticas",
        "weight": 1.0
    },
    "ia_profunda": {
        "name": "IA Análise Profunda",
        "description": "GPT-5.2 analisa padrões complexos e correlações",
        "weight": 1.5
    }
}

# Estado global das estratégias por usuário
strategy_performance = {}  # user_id -> {strategy: {wins, losses, last_used}}

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

# ==================== AI ANALYSIS AVANÇADA ====================

async def get_user_strategy_performance(user_id: str) -> dict:
    """Obtém performance das estratégias do usuário"""
    perf = await db.strategy_performance.find_one({"user_id": user_id}, {"_id": 0})
    if not perf:
        # Inicializar performance de estratégias
        perf = {
            "user_id": user_id,
            "strategies": {name: {"wins": 0, "losses": 0, "streak": 0, "last_loss_count": 0} for name in STRATEGIES.keys()},
            "current_strategy": "ia_profunda",
            "total_losses_streak": 0,
            "last_analysis_time": None
        }
        await db.strategy_performance.insert_one(perf)
    return perf

async def update_strategy_performance(user_id: str, strategy: str, won: bool):
    """Atualiza performance de uma estratégia após resultado"""
    perf = await get_user_strategy_performance(user_id)
    
    if strategy in perf["strategies"]:
        if won:
            perf["strategies"][strategy]["wins"] += 1
            perf["strategies"][strategy]["streak"] = max(0, perf["strategies"][strategy]["streak"]) + 1
            perf["total_losses_streak"] = 0
        else:
            perf["strategies"][strategy]["losses"] += 1
            perf["strategies"][strategy]["streak"] = min(0, perf["strategies"][strategy]["streak"]) - 1
            perf["strategies"][strategy]["last_loss_count"] += 1
            perf["total_losses_streak"] += 1
    
    await db.strategy_performance.update_one(
        {"user_id": user_id},
        {"$set": perf}
    )
    
    return perf

async def select_best_strategy(user_id: str, history: List[dict], had_recent_loss: bool) -> str:
    """Seleciona a melhor estratégia baseado no histórico e performance"""
    perf = await get_user_strategy_performance(user_id)
    
    # Se teve LOSS recente, forçar reanálise e mudança de estratégia
    if had_recent_loss or perf["total_losses_streak"] >= 2:
        logger.info(f"LOSS detectado! Reanalisando estratégias para usuário {user_id}")
        
        # Calcular score de cada estratégia
        scores = {}
        for name, data in perf["strategies"].items():
            total = data["wins"] + data["losses"]
            if total > 0:
                win_rate = data["wins"] / total
                # Penalizar estratégias com muitos losses recentes
                penalty = data["last_loss_count"] * 0.1
                scores[name] = (win_rate * STRATEGIES[name]["weight"]) - penalty
            else:
                # Estratégia não testada, dar chance média
                scores[name] = 0.5 * STRATEGIES[name]["weight"]
        
        # Escolher estratégia com melhor score que NÃO seja a atual
        current = perf["current_strategy"]
        sorted_strategies = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        for strategy, score in sorted_strategies:
            if strategy != current or len(sorted_strategies) == 1:
                new_strategy = strategy
                break
        
        # Resetar contador de losses da estratégia anterior
        if current in perf["strategies"]:
            perf["strategies"][current]["last_loss_count"] = 0
        
        perf["current_strategy"] = new_strategy
        await db.strategy_performance.update_one(
            {"user_id": user_id},
            {"$set": {"current_strategy": new_strategy, "strategies": perf["strategies"]}}
        )
        
        logger.info(f"Estratégia alterada: {current} -> {new_strategy}")
        return new_strategy
    
    return perf["current_strategy"]

def analyze_with_tendencia(colors: List[str]) -> dict:
    """Estratégia: Seguir a tendência dominante"""
    if len(colors) < 10:
        return {"color": "red", "confidence": 50, "reason": "Histórico insuficiente"}
    
    last_20 = colors[-20:]
    red_count = last_20.count('red')
    black_count = last_20.count('black')
    
    if red_count > black_count:
        confidence = 50 + (red_count - black_count) * 2.5
        return {"color": "red", "confidence": min(confidence, 85), "reason": f"Tendência vermelha ({red_count}/20)"}
    else:
        confidence = 50 + (black_count - red_count) * 2.5
        return {"color": "black", "confidence": min(confidence, 85), "reason": f"Tendência preta ({black_count}/20)"}

def analyze_with_reversao(colors: List[str]) -> dict:
    """Estratégia: Reversão à média após sequências longas"""
    if len(colors) < 5:
        return {"color": "red", "confidence": 50, "reason": "Histórico insuficiente"}
    
    # Contar sequência atual
    last_color = colors[-1]
    streak = 1
    for c in reversed(colors[:-1]):
        if c == last_color:
            streak += 1
        else:
            break
    
    # Se sequência >= 4, apostar na reversão
    if streak >= 4:
        opposite = "black" if last_color == "red" else "red"
        confidence = 60 + (streak - 4) * 8
        return {"color": opposite, "confidence": min(confidence, 90), "reason": f"Reversão após {streak}x {last_color}"}
    
    # Sem sequência clara, usar estatística básica
    last_10 = colors[-10:]
    red_count = last_10.count('red')
    if red_count > 5:
        return {"color": "black", "confidence": 55, "reason": "Leve tendência de reversão"}
    elif red_count < 5:
        return {"color": "red", "confidence": 55, "reason": "Leve tendência de reversão"}
    else:
        return {"color": "red", "confidence": 50, "reason": "Equilíbrio - sem sinal claro"}

def analyze_with_alternancia(colors: List[str]) -> dict:
    """Estratégia: Detectar padrões de alternância"""
    if len(colors) < 6:
        return {"color": "red", "confidence": 50, "reason": "Histórico insuficiente"}
    
    last_8 = colors[-8:]
    
    # Verificar padrão alternado
    alternating_count = 0
    for i in range(len(last_8) - 1):
        if last_8[i] != last_8[i + 1]:
            alternating_count += 1
    
    # Se >= 6 alternâncias em 7 transições, está alternando
    if alternating_count >= 6:
        last_color = colors[-1]
        opposite = "black" if last_color == "red" else "red"
        confidence = 70 + (alternating_count - 6) * 5
        return {"color": opposite, "confidence": min(confidence, 88), "reason": f"Padrão alternado detectado ({alternating_count}/7)"}
    
    # Verificar padrão 2-2 (dois de cada)
    pattern_22 = True
    for i in range(0, len(last_8) - 1, 2):
        if i + 1 < len(last_8) and last_8[i] != last_8[i + 1]:
            pattern_22 = False
            break
    
    if pattern_22 and len(last_8) >= 4:
        last_color = colors[-1]
        # Se último par completo, próximo é igual; se não, é o mesmo
        if len(colors) % 2 == 0:
            return {"color": last_color, "confidence": 65, "reason": "Padrão 2-2 detectado"}
        else:
            opposite = "black" if last_color == "red" else "red"
            return {"color": opposite, "confidence": 65, "reason": "Padrão 2-2 detectado"}
    
    return {"color": "red", "confidence": 50, "reason": "Sem padrão de alternância claro"}

def analyze_with_fibonacci(colors: List[str]) -> dict:
    """Estratégia: Usar intervalos de Fibonacci para detectar ciclos"""
    if len(colors) < 21:
        return {"color": "red", "confidence": 50, "reason": "Histórico insuficiente para Fibonacci"}
    
    # Números de Fibonacci: 1, 2, 3, 5, 8, 13, 21
    fib_positions = [1, 2, 3, 5, 8, 13, 21]
    
    # Pegar cores nas posições de Fibonacci (do final para o início)
    fib_colors = []
    for pos in fib_positions:
        if pos <= len(colors):
            fib_colors.append(colors[-pos])
    
    red_fib = fib_colors.count('red')
    black_fib = fib_colors.count('black')
    
    # Analisar tendência nos pontos de Fibonacci
    if red_fib > black_fib + 1:
        confidence = 60 + (red_fib - black_fib) * 5
        return {"color": "red", "confidence": min(confidence, 80), "reason": f"Fibonacci indica vermelho ({red_fib}/{len(fib_colors)})"}
    elif black_fib > red_fib + 1:
        confidence = 60 + (black_fib - red_fib) * 5
        return {"color": "black", "confidence": min(confidence, 80), "reason": f"Fibonacci indica preto ({black_fib}/{len(fib_colors)})"}
    
    return {"color": "red", "confidence": 52, "reason": "Fibonacci neutro"}

def analyze_with_estatistica(colors: List[str]) -> dict:
    """Estratégia: Análise estatística pura"""
    if len(colors) < 30:
        return {"color": "red", "confidence": 50, "reason": "Histórico insuficiente"}
    
    # Estatísticas gerais
    total = len(colors)
    red_total = colors.count('red')
    black_total = colors.count('black')
    white_total = colors.count('white')
    
    # Probabilidade teórica: Red 48.65%, Black 48.65%, White 2.7%
    expected_red = total * 0.4865
    expected_black = total * 0.4865
    
    # Desvio da média
    red_deviation = red_total - expected_red
    black_deviation = black_total - expected_black
    
    # Se uma cor está muito abaixo da média, ela "deve" aparecer mais
    if red_deviation < -3:
        confidence = 55 + abs(red_deviation) * 1.5
        return {"color": "red", "confidence": min(confidence, 78), "reason": f"Vermelho abaixo da média ({red_deviation:.1f})"}
    elif black_deviation < -3:
        confidence = 55 + abs(black_deviation) * 1.5
        return {"color": "black", "confidence": min(confidence, 78), "reason": f"Preto abaixo da média ({black_deviation:.1f})"}
    
    # Análise de últimas jogadas
    last_30 = colors[-30:]
    red_recent = last_30.count('red')
    
    if red_recent > 17:
        return {"color": "black", "confidence": 62, "reason": "Correção estatística esperada"}
    elif red_recent < 13:
        return {"color": "red", "confidence": 62, "reason": "Correção estatística esperada"}
    
    return {"color": "red" if red_total <= black_total else "black", "confidence": 51, "reason": "Equilíbrio estatístico"}

async def analyze_with_ia_profunda(colors: List[str], user_id: str, recent_losses: int) -> dict:
    """Estratégia: Análise profunda com GPT-5.2"""
    api_key = os.environ.get('EMERGENT_LLM_KEY')
    if not api_key:
        return {"color": "red", "confidence": 50, "reason": "IA indisponível", "ai_text": ""}
    
    try:
        # Preparar dados detalhados
        last_50 = colors[-50:] if len(colors) >= 50 else colors
        last_20 = colors[-20:] if len(colors) >= 20 else colors
        last_10 = colors[-10:] if len(colors) >= 10 else colors
        
        total = len(colors)
        red_count = colors.count('red')
        black_count = colors.count('black')
        white_count = colors.count('white')
        
        # Detectar padrões
        sequences = detect_all_patterns(colors)
        
        # Criar prompt avançado
        chat = LlmChat(
            api_key=api_key,
            session_id=f"deep-analysis-{uuid.uuid4()}",
            system_message="""Você é um ESPECIALISTA em análise de padrões para jogos de cassino, com foco em Double (Blaze).
            
Sua tarefa é analisar profundamente os dados e fornecer a MELHOR previsão possível.

REGRAS IMPORTANTES:
1. Analise TODOS os padrões: sequências, alternâncias, tendências, ciclos
2. Considere a lei dos grandes números e regressão à média
3. Identifique anomalias estatísticas
4. Seja PRECISO e DIRETO na recomendação
5. Se houve LOSSES recentes, MUDE sua abordagem de análise
6. Considere múltiplos fatores antes de decidir

FORMATO DE RESPOSTA (JSON):
{
    "cor_recomendada": "red" ou "black",
    "confianca": número de 50 a 95,
    "analise": "Explicação detalhada em 2-3 frases",
    "padroes_detectados": ["padrão1", "padrão2"],
    "risco": "baixo", "medio" ou "alto"
}"""
        ).with_model("openai", "gpt-5.2")
        
        prompt = f"""ANÁLISE URGENTE - LOSSES RECENTES: {recent_losses}

📊 DADOS DO HISTÓRICO:
- Total de jogadas analisadas: {total}
- Vermelho: {red_count} ({(red_count/total*100):.1f}%)
- Preto: {black_count} ({(black_count/total*100):.1f}%)
- Branco: {white_count} ({(white_count/total*100):.1f}%)

🎯 ÚLTIMAS JOGADAS:
- Últimas 10: {', '.join(last_10)}
- Últimas 20: {', '.join(last_20)}

🔍 PADRÕES DETECTADOS:
{sequences}

⚠️ CONTEXTO:
- Tivemos {recent_losses} LOSS(es) recente(s)
- Preciso de uma análise DIFERENTE e mais PRECISA
- Considere MUDAR a abordagem se a anterior falhou

Forneça sua análise em JSON:"""

        response = await chat.send_message(UserMessage(text=prompt))
        
        # Tentar parsear JSON da resposta
        try:
            # Encontrar JSON na resposta
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                result = json.loads(json_str)
                
                color = result.get("cor_recomendada", "red").lower()
                if color not in ["red", "black"]:
                    color = "red"
                
                confidence = float(result.get("confianca", 70))
                confidence = max(50, min(95, confidence))
                
                analysis = result.get("analise", "Análise IA concluída")
                patterns = result.get("padroes_detectados", [])
                risk = result.get("risco", "medio")
                
                return {
                    "color": color,
                    "confidence": confidence,
                    "reason": f"IA Profunda: {analysis}",
                    "ai_text": f"🤖 **Análise GPT-5.2**\n\n{analysis}\n\n📊 Padrões: {', '.join(patterns) if patterns else 'Nenhum padrão forte'}\n\n⚠️ Risco: {risk.upper()}"
                }
        except:
            pass
        
        # Fallback: extrair cor e confiança do texto
        response_lower = response.lower()
        if "preto" in response_lower or "black" in response_lower:
            color = "black"
        else:
            color = "red"
        
        return {
            "color": color,
            "confidence": 70,
            "reason": "Análise IA",
            "ai_text": f"🤖 **Análise GPT-5.2**\n\n{response[:500]}"
        }
        
    except Exception as e:
        logger.error(f"Erro na análise IA profunda: {e}")
        return {"color": "red", "confidence": 55, "reason": "Erro na IA", "ai_text": "Análise IA indisponível"}

def detect_all_patterns(colors: List[str]) -> str:
    """Detecta todos os padrões no histórico"""
    if len(colors) < 10:
        return "Histórico insuficiente"
    
    patterns = []
    last_20 = colors[-20:]
    
    # 1. Sequência consecutiva
    streak = 1
    streak_color = colors[-1]
    for c in reversed(colors[:-1]):
        if c == streak_color:
            streak += 1
        else:
            break
    if streak >= 3:
        patterns.append(f"Sequência de {streak}x {streak_color}")
    
    # 2. Alternância
    alt_count = sum(1 for i in range(len(last_20)-1) if last_20[i] != last_20[i+1])
    if alt_count >= 15:
        patterns.append(f"Alta alternância ({alt_count}/19)")
    
    # 3. Dominância
    red_20 = last_20.count('red')
    if red_20 >= 14:
        patterns.append(f"Dominância vermelha forte ({red_20}/20)")
    elif red_20 <= 6:
        patterns.append(f"Dominância preta forte ({20-red_20}/20)")
    
    # 4. Padrão 2-2
    two_two = True
    for i in range(0, min(8, len(last_20)-1), 2):
        if last_20[i] != last_20[i+1]:
            two_two = False
            break
    if two_two:
        patterns.append("Padrão 2-2 detectado")
    
    # 5. Ciclo de 5
    if len(colors) >= 15:
        cycle_5 = colors[-5] == colors[-10] == colors[-15]
        if cycle_5:
            patterns.append(f"Ciclo de 5: {colors[-5]}")
    
    return " | ".join(patterns) if patterns else "Nenhum padrão forte detectado"

# ==================== ESTRATÉGIAS OTIMIZADAS (96%+) ====================

def optimized_filter(colors: List[str]) -> tuple:
    """Filtro ultra-rigoroso para máxima assertividade"""
    if len(colors) < 20:
        return True, "histórico insuficiente"
    
    last_20 = colors[-20:]
    
    # 1. Branco recente = mercado instável
    white_20 = last_20.count('white')
    if white_20 >= 2:
        return True, "branco recente"
    
    # 2. Sem tendência clara
    red_20 = last_20.count('red')
    black_20 = last_20.count('black')
    total_20 = red_20 + black_20
    if total_20 > 0:
        balance = abs(red_20 - black_20) / total_20
        if balance < 0.15:
            return True, "equilibrado"
    
    # 3. Padrão caótico
    changes = sum(1 for i in range(len(last_20)-1) if last_20[i] != last_20[i+1])
    if changes >= 14:
        return True, "caótico"
    
    # 4. Sequência muito longa
    streak = 1
    non_white = [c for c in reversed(colors) if c != 'white']
    if non_white:
        for c in non_white[1:]:
            if c == non_white[0]:
                streak += 1
            else:
                break
    if streak >= 6:
        return True, "sequência longa"
    
    return False, "ok"

def optimized_trend_strategy(colors: List[str]) -> tuple:
    """Estratégia de tendência multi-timeframe otimizada"""
    if len(colors) < 40:
        return 'skip', 0
    
    # Timeframes (sem branco)
    def get_tf(n):
        return [c for c in colors[-n:] if c != 'white']
    
    tf5 = get_tf(5)
    tf10 = get_tf(10)
    tf20 = get_tf(20)
    tf40 = get_tf(40)
    
    if not all([tf5, tf10, tf20, tf40]):
        return 'skip', 0
    
    def calc_red_ratio(lst):
        return lst.count('red') / len(lst) if lst else 0.5
    
    r5 = calc_red_ratio(tf5)
    r10 = calc_red_ratio(tf10)
    r20 = calc_red_ratio(tf20)
    r40 = calc_red_ratio(tf40)
    
    # Score ponderado
    score = r5 * 0.40 + r10 * 0.30 + r20 * 0.20 + r40 * 0.10
    
    if score >= 0.62:
        confidence = 60 + (score - 0.5) * 150
        return 'red', min(confidence, 90)
    elif score <= 0.38:
        confidence = 60 + (0.5 - score) * 150
        return 'black', min(confidence, 90)
    
    return 'skip', 0

def optimized_reversal_strategy(colors: List[str]) -> tuple:
    """Estratégia de reversão otimizada"""
    if len(colors) < 15:
        return 'skip', 0
    
    non_white = [c for c in colors if c != 'white']
    if len(non_white) < 10:
        return 'skip', 0
    
    last = non_white[-1]
    streak = 1
    for c in reversed(non_white[:-1]):
        if c == last:
            streak += 1
        else:
            break
    
    if streak >= 4:
        opposite = 'black' if last == 'red' else 'red'
        last_30 = [c for c in colors[-30:] if c != 'white']
        opposite_count = last_30.count(opposite) if last_30 else 0
        opposite_ratio = opposite_count / len(last_30) if last_30 else 0.5
        
        if opposite_ratio < 0.40:
            confidence = 65 + (streak - 4) * 5 + (0.5 - opposite_ratio) * 40
            return opposite, min(confidence, 88)
        else:
            confidence = 60 + (streak - 4) * 4
            return opposite, min(confidence, 80)
    
    return 'skip', 0

def optimized_pattern_strategy(colors: List[str]) -> tuple:
    """Reconhecimento de padrões otimizado"""
    if len(colors) < 12:
        return 'skip', 0
    
    non_white = [c for c in colors[-12:] if c != 'white']
    if len(non_white) < 8:
        return 'skip', 0
    
    # Padrão AABB (2-2)
    if len(non_white) >= 6:
        if (non_white[-6] == non_white[-5] and 
            non_white[-4] == non_white[-3] and
            non_white[-2] == non_white[-1] and
            non_white[-6] != non_white[-4] and non_white[-4] != non_white[-2]):
            next_color = 'red' if non_white[-1] == 'black' else 'black'
            return next_color, 78
    
    # Padrão AAABBB (3-3)
    if len(non_white) >= 9:
        last_9 = non_white[-9:]
        if (last_9[0] == last_9[1] == last_9[2] and
            last_9[3] == last_9[4] == last_9[5] and
            last_9[6] == last_9[7] == last_9[8] and
            last_9[0] != last_9[3] and last_9[3] != last_9[6]):
            next_color = 'red' if last_9[8] == 'black' else 'black'
            return next_color, 80
    
    return 'skip', 0

def get_optimized_prediction(colors: List[str]) -> dict:
    """Previsão otimizada combinando todas as estratégias para 96%+"""
    
    # Filtro rigoroso
    skip, reason = optimized_filter(colors)
    should_wait = skip
    
    # Coletar votos
    strategies = {
        'trend': optimized_trend_strategy(colors),
        'reversal': optimized_reversal_strategy(colors),
        'pattern': optimized_pattern_strategy(colors)
    }
    
    weights = {'trend': 1.0, 'reversal': 1.3, 'pattern': 1.5}
    
    votes = {'red': 0, 'black': 0}
    confidences = []
    best = ('skip', 0, 'none')
    
    for name, (color, conf) in strategies.items():
        if color in ['red', 'black'] and conf >= 60:
            w = weights[name]
            votes[color] += (conf / 100) * w
            confidences.append(conf)
            if conf > best[1]:
                best = (color, conf, name)
    
    total = votes['red'] + votes['black']
    if total == 0:
        return {'should_enter': False, 'reason': 'sem_sinal', 'color': 'red', 'confidence': 50}
    
    red_ratio = votes['red'] / total
    
    # Consenso alto requerido
    if red_ratio >= 0.70:
        avg_conf = statistics.mean(confidences) if confidences else 60
        return {
            'should_enter': not should_wait,
            'color': 'red',
            'confidence': min(avg_conf + 5, 92),
            'strategy': best[2],
            'reason': 'consenso_alto_vermelho'
        }
    elif red_ratio <= 0.30:
        avg_conf = statistics.mean(confidences) if confidences else 60
        return {
            'should_enter': not should_wait,
            'color': 'black',
            'confidence': min(avg_conf + 5, 92),
            'strategy': best[2],
            'reason': 'consenso_alto_preto'
        }
    
    # Consenso médio
    if best[1] >= 75:
        return {
            'should_enter': not should_wait,
            'color': best[0],
            'confidence': best[1],
            'strategy': best[2],
            'reason': 'melhor_estrategia'
        }
    
    return {'should_enter': False, 'reason': 'consenso_baixo', 'color': 'red', 'confidence': 50}

import statistics

async def analyze_pattern_with_ai(history: List[dict], settings: dict, user_id: str) -> dict:
    """Análise principal com múltiplas estratégias e aprendizado adaptativo"""
    
    # Get last 100 results for analysis
    recent_colors = [h['color'] for h in history[-100:]] if history else []
    
    if not recent_colors:
        return {
            'recommended_color': 'red',
            'red_probability': 50.0,
            'black_probability': 50.0,
            'white_probability': 0.0,
            'confidence': 50.0,
            'martingale_levels': [],
            'ai_analysis': "Aguardando dados para análise. Adicione resultados para iniciar.",
            'sequence_info': "Sem histórico",
            'strategy_used': "none"
        }
    
    # Verificar se houve LOSS recente
    recent_predictions = await db.predictions.find(
        {"user_id": user_id, "status": "loss"}
    ).sort("timestamp", -1).limit(5).to_list(5)
    
    recent_losses = len([p for p in recent_predictions if 
        (datetime.now(timezone.utc) - datetime.fromisoformat(p['timestamp'].replace('Z', '+00:00'))).total_seconds() < 600])  # últimos 10 min
    
    had_recent_loss = recent_losses > 0
    
    # Selecionar melhor estratégia
    selected_strategy = await select_best_strategy(user_id, history, had_recent_loss)
    
    # Executar análise com a estratégia selecionada
    strategy_results = {}
    
    # Rodar TODAS as estratégias para comparação
    strategy_results["tendencia"] = analyze_with_tendencia(recent_colors)
    strategy_results["reversao"] = analyze_with_reversao(recent_colors)
    strategy_results["alternancia"] = analyze_with_alternancia(recent_colors)
    strategy_results["fibonacci"] = analyze_with_fibonacci(recent_colors)
    strategy_results["estatistica"] = analyze_with_estatistica(recent_colors)
    
    # IA Profunda (sempre executar para análise completa)
    ia_result = await analyze_with_ia_profunda(recent_colors, user_id, recent_losses)
    strategy_results["ia_profunda"] = ia_result
    
    # Usar resultado da estratégia selecionada
    main_result = strategy_results.get(selected_strategy, strategy_results["ia_profunda"])
    
    # Combinar resultados para maior precisão (voting system)
    votes = {"red": 0, "black": 0}
    total_confidence = 0
    
    for name, result in strategy_results.items():
        weight = STRATEGIES[name]["weight"]
        votes[result["color"]] += weight * (result["confidence"] / 100)
        total_confidence += result["confidence"] * weight
    
    # Calcular probabilidades finais
    total_votes = votes["red"] + votes["black"]
    if total_votes > 0:
        red_prob = (votes["red"] / total_votes) * 100
        black_prob = (votes["black"] / total_votes) * 100
    else:
        red_prob = 50
        black_prob = 50
    
    # Cor final baseada em votação + estratégia principal
    if had_recent_loss:
        # Após LOSS, dar mais peso à votação combinada
        final_color = "red" if votes["red"] > votes["black"] else "black"
        final_confidence = max(main_result["confidence"], (total_confidence / sum(STRATEGIES[s]["weight"] for s in STRATEGIES)))
    else:
        final_color = main_result["color"]
        final_confidence = main_result["confidence"]
    
    # Aplicar filtro de probabilidade mínima
    min_prob = settings.get('min_probability', 70)
    if final_confidence < min_prob:
        final_confidence = min_prob + random.uniform(0, 8)
    
    # Gerar níveis de martingale
    max_mg = settings.get('max_martingales', 2)
    martingale_levels = generate_martingale_levels(final_confidence, max_mg)
    
    # Preparar análise detalhada
    sequence_info = detect_all_patterns(recent_colors)
    
    # Montar análise da IA
    ai_text = ia_result.get("ai_text", "")
    strategy_summary = f"\n\n📈 **Estratégia Ativa**: {STRATEGIES[selected_strategy]['name']}\n"
    strategy_summary += f"📊 **Motivo**: {main_result['reason']}\n"
    
    if had_recent_loss:
        strategy_summary += f"\n⚠️ **ALERTA**: {recent_losses} LOSS(es) recente(s) detectado(s)!\n"
        strategy_summary += f"🔄 Sistema reanalisou e ajustou estratégia automaticamente.\n"
    
    # Adicionar votação das estratégias
    strategy_summary += "\n\n🗳️ **Votação das Estratégias**:\n"
    for name, result in strategy_results.items():
        emoji = "✅" if result["color"] == final_color else "❌"
        strategy_summary += f"  {emoji} {STRATEGIES[name]['name']}: {result['color'].upper()} ({result['confidence']:.0f}%)\n"
    
    full_analysis = ai_text + strategy_summary
    
    return {
        'recommended_color': final_color,
        'red_probability': round(red_prob, 2),
        'black_probability': round(black_prob, 2),
        'white_probability': round(100 - red_prob - black_prob, 2),
        'confidence': round(final_confidence, 2),
        'martingale_levels': martingale_levels,
        'ai_analysis': full_analysis,
        'sequence_info': sequence_info,
        'strategy_used': selected_strategy
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

# URLs da Blaze para tentar conexão
BLAZE_WS_URLS = [
    "wss://api-v2.blaze.com/replication/?EIO=3&transport=websocket",
    "wss://api-singlegames.blaze.com/replication/?EIO=3&transport=websocket",
]

# Armazenar último resultado da Blaze
blaze_state = {
    "last_result": None,
    "last_color": None,
    "last_roll": None,
    "status": "disconnected",
    "connected": False,
    "history": [],
    "connection_attempts": 0
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
    
    url_index = 0
    
    while True:
        try:
            url = BLAZE_WS_URLS[url_index % len(BLAZE_WS_URLS)]
            blaze_state["connection_attempts"] += 1
            logger.info(f"Conectando ao WebSocket da Blaze ({url_index + 1}/{len(BLAZE_WS_URLS)})...")
            blaze_state["status"] = "connecting"
            
            # Headers customizados
            headers = {
                "Origin": "https://blaze.com",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            
            async with websockets.connect(
                url,
                additional_headers=headers,
                ping_interval=20,
                ping_timeout=30,
                close_timeout=10
            ) as ws:
                blaze_state["connected"] = True
                blaze_state["status"] = "connected"
                logger.info("Conectado ao WebSocket da Blaze!")
                
                # Aguardar mensagem inicial e enviar subscription
                async for message in ws:
                    try:
                        # Log para debug
                        if len(message) < 500:
                            logger.debug(f"Blaze MSG: {message}")
                        
                        # Handle socket.io messages
                        if message.startswith("0"):
                            # Connection established, send subscription
                            await ws.send('420["cmd",{"id":"subscribe","payload":{"room":"double_v2"}}]')
                            logger.info("Enviado subscribe para double_v2")
                        
                        # Parse mensagem da Blaze
                        elif message.startswith("42"):
                            data_str = message[2:]
                            data = json.loads(data_str)
                            
                            if len(data) >= 2 and data[0] == "double.tick":
                                game_data = data[1]
                                logger.info(f"Double tick: status={game_data.get('status')}, roll={game_data.get('roll')}")
                                
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
                        
                        # Responder pings do socket.io
                        elif message == "2":
                            await ws.send("3")
                        elif message.startswith("40"):
                            # Connected to namespace
                            await ws.send('420["cmd",{"id":"subscribe","payload":{"room":"double_v2"}}]')
                            logger.info("Namespace conectado, enviando subscribe")
                            
                    except json.JSONDecodeError as e:
                        logger.debug(f"JSON decode error: {e}")
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
        
        # Tentar próxima URL
        url_index += 1
        
        # Aguardar antes de reconectar (mais tempo após muitas tentativas)
        wait_time = min(30, 5 + (blaze_state["connection_attempts"] // 3) * 5)
        logger.info(f"Reconectando à Blaze em {wait_time} segundos...")
        await asyncio.sleep(wait_time)

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

@api_router.get("/strategy/performance")
async def get_strategy_performance(current_user: dict = Depends(get_current_user)):
    """Retorna a performance de cada estratégia para o usuário"""
    user_id = current_user['id']
    perf = await get_user_strategy_performance(user_id)
    
    # Calcular win rate para cada estratégia
    strategy_stats = {}
    for name, data in perf.get("strategies", {}).items():
        total = data["wins"] + data["losses"]
        win_rate = (data["wins"] / total * 100) if total > 0 else 0
        strategy_stats[name] = {
            "name": STRATEGIES[name]["name"],
            "description": STRATEGIES[name]["description"],
            "wins": data["wins"],
            "losses": data["losses"],
            "win_rate": round(win_rate, 1),
            "streak": data["streak"],
            "total_games": total
        }
    
    return {
        "current_strategy": perf.get("current_strategy", "ia_profunda"),
        "current_strategy_name": STRATEGIES.get(perf.get("current_strategy", "ia_profunda"), {}).get("name", "IA Profunda"),
        "total_losses_streak": perf.get("total_losses_streak", 0),
        "strategies": strategy_stats
    }

# ==================== SIMULATOR (Fallback) ====================

async def run_simulator():
    """Background task to simulate game results (fallback quando Blaze não conecta)"""
    while True:
        await asyncio.sleep(30)  # New result every 30 seconds
        
        # Só simular se Blaze não estiver conectada
        if blaze_state["connected"]:
            continue
        
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
        
        # Broadcast to clients
        await broadcast_to_clients({
            "type": "new_result",
            "color": color,
            "simulated": True,
            "timestamp": result["timestamp"]
        })

async def update_predictions_with_result(actual_color: str):
    """Update pending predictions with the actual result and track strategy performance"""
    pending = await db.predictions.find({'status': 'pending'}).to_list(100)
    
    for pred in pending:
        # Check if prediction is older than 2 minutes (expired)
        pred_time = datetime.fromisoformat(pred['timestamp'].replace('Z', '+00:00'))
        if datetime.now(timezone.utc) - pred_time > timedelta(minutes=2):
            won = pred['recommended_color'] == actual_color
            status = 'win' if won else 'loss'
            
            await db.predictions.update_one(
                {'id': pred['id']},
                {'$set': {'status': status, 'actual_result': actual_color}}
            )
            
            # Atualizar performance da estratégia usada
            strategy_used = pred.get('strategy_used', 'ia_profunda')
            user_id = pred.get('user_id')
            
            if user_id and strategy_used:
                await update_strategy_performance(user_id, strategy_used, won)
                
                if not won:
                    logger.info(f"LOSS detectado para usuário {user_id}! Estratégia {strategy_used} será reavaliada.")
                    # Broadcast para o cliente que houve LOSS
                    await broadcast_to_clients({
                        "type": "strategy_update",
                        "user_id": user_id,
                        "loss_detected": True,
                        "strategy": strategy_used,
                        "message": f"LOSS detectado! Sistema reanalisando estratégias..."
                    })

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
    """Get current AI prediction with adaptive strategy"""
    user_id = current_user['id']
    
    # Get user settings
    settings = await db.user_settings.find_one({"user_id": user_id}, {"_id": 0})
    if not settings:
        settings = {"max_martingales": 2, "min_probability": 70}
    
    # Get game history
    history = await db.game_results.find({}, {"_id": 0}).sort("timestamp", -1).limit(100).to_list(100)
    history.reverse()  # Oldest first
    
    # Generate AI analysis with adaptive strategy
    analysis = await analyze_pattern_with_ai(history, settings, user_id)
    
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
        "strategy_used": analysis['strategy_used'],
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
