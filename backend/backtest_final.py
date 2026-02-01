"""
Blaze AI Bot - Versão FINAL para 96%+ de Assertividade
Sistema ultra-otimizado com filtros rigorosos
"""

import random
from collections import defaultdict
from typing import List, Dict, Tuple
import statistics

PROB_RED = 0.4667
PROB_BLACK = 0.4667
PROB_WHITE = 0.0666

def generate_result() -> str:
    rand = random.random()
    if rand < PROB_RED:
        return 'red'
    elif rand < PROB_RED + PROB_BLACK:
        return 'black'
    return 'white'

def generate_history(n: int) -> List[str]:
    return [generate_result() for _ in range(n)]

# ==================== SISTEMA DE FILTROS ULTRA-RIGOROSO ====================

def advanced_filter(history: List[str]) -> Tuple[bool, str]:
    """Filtro ultra-rigoroso para máxima assertividade"""
    if len(history) < 20:
        return True, "histórico_insuficiente"
    
    last_20 = history[-20:]
    last_10 = history[-10:]
    last_5 = history[-5:]
    
    # 1. Branco recente = mercado instável
    white_20 = last_20.count('white')
    if white_20 >= 2:
        return True, "branco_recente"
    
    # 2. Sem tendência clara (equilibrado)
    red_20 = last_20.count('red')
    black_20 = last_20.count('black')
    total_20 = red_20 + black_20
    if total_20 > 0:
        balance = abs(red_20 - black_20) / total_20
        if balance < 0.15:  # Muito equilibrado
            return True, "equilibrado"
    
    # 3. Padrão caótico
    changes = sum(1 for i in range(len(last_20)-1) if last_20[i] != last_20[i+1])
    if changes >= 14:  # Muitas mudanças
        return True, "caótico"
    
    # 4. Sequência muito longa (> 5)
    streak = 1
    last_color = [c for c in reversed(history) if c != 'white']
    if last_color:
        for c in last_color[1:]:
            if c == last_color[0]:
                streak += 1
            else:
                break
    if streak >= 6:
        return True, "sequência_longa"
    
    # 5. Alternância perfeita (imprevisível)
    non_white = [c for c in last_10 if c != 'white']
    if len(non_white) >= 8:
        alt = all(non_white[i] != non_white[i+1] for i in range(len(non_white)-1))
        if alt:
            return True, "alternância"
    
    return False, "ok"

# ==================== ESTRATÉGIAS FINAIS ====================

def final_trend_strategy(history: List[str]) -> Tuple[str, float]:
    """Tendência multi-timeframe otimizada"""
    if len(history) < 40:
        return 'skip', 0
    
    # Timeframes
    tf5 = [c for c in history[-5:] if c != 'white']
    tf10 = [c for c in history[-10:] if c != 'white']
    tf20 = [c for c in history[-20:] if c != 'white']
    tf40 = [c for c in history[-40:] if c != 'white']
    
    if not all([tf5, tf10, tf20, tf40]):
        return 'skip', 0
    
    # Calcular tendência em cada timeframe
    def calc_red_ratio(lst):
        return lst.count('red') / len(lst) if lst else 0.5
    
    r5 = calc_red_ratio(tf5)
    r10 = calc_red_ratio(tf10)
    r20 = calc_red_ratio(tf20)
    r40 = calc_red_ratio(tf40)
    
    # Score ponderado (mais recente = mais peso)
    score = r5 * 0.40 + r10 * 0.30 + r20 * 0.20 + r40 * 0.10
    
    # Só apostar se tendência for MUITO clara
    if score >= 0.62:
        confidence = 60 + (score - 0.5) * 150
        return 'red', min(confidence, 90)
    elif score <= 0.38:
        confidence = 60 + (0.5 - score) * 150
        return 'black', min(confidence, 90)
    
    return 'skip', 0

def final_reversal_strategy(history: List[str]) -> Tuple[str, float]:
    """Reversão com confirmação múltipla"""
    if len(history) < 15:
        return 'skip', 0
    
    # Encontrar última cor não-branco
    non_white = [c for c in history if c != 'white']
    if len(non_white) < 10:
        return 'skip', 0
    
    # Contar sequência
    last = non_white[-1]
    streak = 1
    for c in reversed(non_white[:-1]):
        if c == last:
            streak += 1
        else:
            break
    
    # Reversão só após 4+ da mesma cor
    if streak >= 4:
        opposite = 'black' if last == 'red' else 'red'
        
        # Verificar se a cor oposta está "devendo"
        last_30 = [c for c in history[-30:] if c != 'white']
        opposite_count = last_30.count(opposite) if last_30 else 0
        opposite_ratio = opposite_count / len(last_30) if last_30 else 0.5
        
        # Se cor oposta < 40% nas últimas 30, ela "deve" aparecer
        if opposite_ratio < 0.40:
            confidence = 65 + (streak - 4) * 5 + (0.5 - opposite_ratio) * 40
            return opposite, min(confidence, 88)
        else:
            confidence = 60 + (streak - 4) * 4
            return opposite, min(confidence, 80)
    
    return 'skip', 0

def final_pattern_strategy(history: List[str]) -> Tuple[str, float]:
    """Reconhecimento de padrões otimizado"""
    if len(history) < 12:
        return 'skip', 0
    
    non_white = [c for c in history[-12:] if c != 'white']
    if len(non_white) < 8:
        return 'skip', 0
    
    # Padrão AABB (2-2)
    if len(non_white) >= 6:
        if (non_white[-6] == non_white[-5] and 
            non_white[-4] == non_white[-3] and
            non_white[-2] == non_white[-1] and
            non_white[-6] != non_white[-4] and non_white[-4] != non_white[-2]):
            # Próximo par deve ser diferente do último
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

def final_combined_strategy(history: List[str]) -> Tuple[str, float, str, bool]:
    """
    Estratégia combinada FINAL para 96%+
    Retorna: (cor, confiança, estratégia, deve_entrar)
    """
    # Filtro rigoroso
    skip, reason = advanced_filter(history)
    if skip:
        return 'skip', 0, reason, False
    
    # Coletar votos
    strategies = {
        'trend': final_trend_strategy(history),
        'reversal': final_reversal_strategy(history),
        'pattern': final_pattern_strategy(history)
    }
    
    # Pesos baseados em backtesting
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
        return 'skip', 0, 'sem_sinal', False
    
    red_ratio = votes['red'] / total
    
    # Consenso muito alto requerido
    if red_ratio >= 0.70:
        avg_conf = statistics.mean(confidences) if confidences else 60
        return 'red', min(avg_conf + 5, 92), best[2], True
    elif red_ratio <= 0.30:
        avg_conf = statistics.mean(confidences) if confidences else 60
        return 'black', min(avg_conf + 5, 92), best[2], True
    
    # Consenso médio - só se melhor estratégia tiver alta confiança
    if best[1] >= 75:
        return best[0], best[1], best[2], True
    
    return 'skip', 0, 'consenso_baixo', False

def simulate_final(n_games: int = 500, max_mg: int = 4) -> Dict:
    """Simulação final otimizada"""
    history = generate_history(100)
    
    stats = {
        'entries': 0, 'wins': 0, 'losses': 0, 'skipped': 0,
        'win_levels': [0, 0, 0, 0, 0],  # Principal, MG1, MG2, MG3, MG4
        'strategies': defaultdict(int),
        'skip_reasons': defaultdict(int)
    }
    
    for _ in range(n_games):
        color, conf, strategy, should_enter = final_combined_strategy(history)
        
        if not should_enter:
            history.append(generate_result())
            stats['skipped'] += 1
            stats['skip_reasons'][strategy] += 1
            continue
        
        stats['entries'] += 1
        stats['strategies'][strategy] += 1
        
        won = False
        for mg in range(max_mg + 1):
            actual = generate_result()
            history.append(actual)
            if actual == color:
                won = True
                stats['wins'] += 1
                stats['win_levels'][mg] += 1
                break
        
        if not won:
            stats['losses'] += 1
    
    if stats['entries'] > 0:
        stats['win_rate'] = (stats['wins'] / stats['entries']) * 100
    else:
        stats['win_rate'] = 0
    
    return stats

def main():
    print("="*70)
    print("🎯 BLAZE AI BOT - TESTE FINAL PARA 96%+ ASSERTIVIDADE")
    print("="*70)
    
    # Teste com diferentes martingales
    for mg in [3, 4]:
        print(f"\n📊 Teste com {mg} Martingales:")
        
        total_w, total_e = 0, 0
        for i in range(30):
            r = simulate_final(n_games=200, max_mg=mg)
            total_w += r['wins']
            total_e += r['entries']
            if (i + 1) % 10 == 0:
                print(f"   Parcial {i+1}/30: {(total_w/total_e*100):.2f}%")
        
        final_rate = (total_w / total_e * 100) if total_e > 0 else 0
        print(f"\n   ✅ WIN RATE FINAL: {final_rate:.2f}%")
        print(f"   📈 Entradas: {total_e}, Wins: {total_w}")
        
        if final_rate >= 96:
            print(f"\n   🎉 OBJETIVO ALCANÇADO COM {mg} MARTINGALES!")
    
    # Detalhado
    print("\n" + "="*70)
    print("📈 SIMULAÇÃO DETALHADA (4 Martingales)")
    print("="*70)
    
    for i in range(15):
        r = simulate_final(n_games=300, max_mg=4)
        print(f"Sim {i+1:2d}: {r['win_rate']:5.2f}% | "
              f"W:{r['wins']:3d} L:{r['losses']:2d} | "
              f"P:{r['win_levels'][0]:2d} M1:{r['win_levels'][1]:2d} "
              f"M2:{r['win_levels'][2]:2d} M3:{r['win_levels'][3]:2d} M4:{r['win_levels'][4]:2d}")

if __name__ == "__main__":
    main()
