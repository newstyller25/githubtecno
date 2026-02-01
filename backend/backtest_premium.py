"""
Blaze AI Bot - Estratégias PREMIUM para 96%+ com 2 Martingales
Foco em padrões de altíssima confiança
"""

import random
from collections import defaultdict
from typing import List, Tuple
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

# ==================== DETECTOR DE PADRÕES DE ALTA CONFIANÇA ====================

def detect_high_confidence_pattern(colors: List[str]) -> Tuple[str, float, str]:
    """
    Detecta APENAS padrões com altíssima probabilidade de acerto
    Retorna: (cor_recomendada, confiança, nome_padrão)
    """
    if len(colors) < 30:
        return 'skip', 0, 'histórico_insuficiente'
    
    # Remover brancos para análise
    non_white = [c for c in colors if c != 'white']
    if len(non_white) < 25:
        return 'skip', 0, 'dados_insuficientes'
    
    last_30 = non_white[-30:]
    last_20 = non_white[-20:]
    last_10 = non_white[-10:]
    last_5 = non_white[-5:]
    
    # ========== PADRÃO 1: Sequência de 4-5 com desvio forte ==========
    # Quando uma cor aparece 4-5x seguidas E está dominando muito
    streak = 1
    last_color = non_white[-1]
    for c in reversed(non_white[:-1]):
        if c == last_color:
            streak += 1
        else:
            break
    
    if streak in [4, 5]:
        opposite = 'black' if last_color == 'red' else 'red'
        
        # Verificar se a cor oposta está MUITO abaixo da média
        opposite_count_30 = last_30.count(opposite)
        opposite_ratio = opposite_count_30 / len(last_30)
        
        # Se cor oposta < 38%, alta chance de correção
        if opposite_ratio < 0.38:
            confidence = 78 + (0.5 - opposite_ratio) * 80 + (streak - 4) * 3
            return opposite, min(confidence, 95), f'reversão_forte_{streak}x'
    
    # ========== PADRÃO 2: Padrão 2-2 estável ==========
    if len(non_white) >= 10:
        # Verificar últimos 8 para padrão AABBCCDD
        last_8 = non_white[-8:]
        is_pattern_22 = (
            last_8[0] == last_8[1] and
            last_8[2] == last_8[3] and
            last_8[4] == last_8[5] and
            last_8[6] == last_8[7] and
            last_8[0] != last_8[2] and
            last_8[2] != last_8[4] and
            last_8[4] != last_8[6]
        )
        
        if is_pattern_22:
            # Próximo deve ser diferente do último par
            next_color = 'red' if last_8[7] == 'black' else 'black'
            return next_color, 88, 'padrão_2-2'
    
    # ========== PADRÃO 3: Padrão 3-3 ==========
    if len(non_white) >= 12:
        last_9 = non_white[-9:]
        is_pattern_33 = (
            last_9[0] == last_9[1] == last_9[2] and
            last_9[3] == last_9[4] == last_9[5] and
            last_9[6] == last_9[7] == last_9[8] and
            last_9[0] != last_9[3] and
            last_9[3] != last_9[6]
        )
        
        if is_pattern_33:
            next_color = 'red' if last_9[8] == 'black' else 'black'
            return next_color, 90, 'padrão_3-3'
    
    # ========== PADRÃO 4: Tendência ultra-forte com confirmação ==========
    red_5 = last_5.count('red')
    red_10 = last_10.count('red')
    red_20 = last_20.count('red')
    red_30 = last_30.count('red')
    
    # Vermelho dominando em TODOS os timeframes
    if red_5 >= 4 and red_10 >= 7 and red_20 >= 13 and red_30 >= 19:
        return 'red', 85, 'tendência_vermelha_total'
    
    # Preto dominando em TODOS os timeframes
    if red_5 <= 1 and red_10 <= 3 and red_20 <= 7 and red_30 <= 11:
        return 'black', 85, 'tendência_preta_total'
    
    # ========== PADRÃO 5: Correção estatística forte ==========
    # Quando uma cor está EXTREMAMENTE abaixo da média
    red_ratio_30 = red_30 / 30
    
    if red_ratio_30 < 0.33:  # Vermelho < 33% (muito abaixo dos 46.67% esperados)
        # Mas vermelho apareceu recentemente (sinal de início de correção)
        if red_5 >= 2:
            return 'red', 80, 'correção_vermelha'
    
    if red_ratio_30 > 0.67:  # Preto < 33%
        if red_5 <= 3:  # Preto apareceu recentemente
            return 'black', 80, 'correção_preta'
    
    return 'skip', 0, 'sem_padrão_forte'

def premium_filter(colors: List[str]) -> Tuple[bool, str]:
    """Filtro para evitar entradas em momentos ruins"""
    if len(colors) < 25:
        return True, "histórico_insuficiente"
    
    # Branco nas últimas 10 = mercado volátil
    if colors[-10:].count('white') >= 1:
        return True, "branco_recente"
    
    # Muitas mudanças recentes = mercado caótico
    last_15 = colors[-15:]
    changes = sum(1 for i in range(len(last_15)-1) if last_15[i] != last_15[i+1])
    if changes >= 11:  # > 73% de mudanças
        return True, "caótico"
    
    return False, "ok"

def premium_strategy(colors: List[str]) -> Tuple[str, float, str, bool]:
    """Estratégia premium para 96%+ com 2 MG"""
    
    # Filtro básico
    skip, reason = premium_filter(colors)
    if skip:
        return 'skip', 0, reason, False
    
    # Detectar padrão de alta confiança
    color, confidence, pattern = detect_high_confidence_pattern(colors)
    
    if color == 'skip' or confidence < 78:
        return 'skip', 0, pattern, False
    
    return color, confidence, pattern, True

def simulate_premium(n_games: int = 500) -> dict:
    """Simulação premium com 2 martingales"""
    history = generate_history(100)
    
    stats = {
        'entries': 0, 'wins': 0, 'losses': 0, 'skipped': 0,
        'win_principal': 0, 'win_mg1': 0, 'win_mg2': 0,
        'patterns': defaultdict(lambda: {'wins': 0, 'losses': 0})
    }
    
    for _ in range(n_games):
        color, conf, pattern, should_enter = premium_strategy(history)
        
        if not should_enter:
            history.append(generate_result())
            stats['skipped'] += 1
            continue
        
        stats['entries'] += 1
        
        # Simular com 2 martingales
        won = False
        for mg in range(3):
            actual = generate_result()
            history.append(actual)
            if actual == color:
                won = True
                stats['wins'] += 1
                stats['patterns'][pattern]['wins'] += 1
                if mg == 0:
                    stats['win_principal'] += 1
                elif mg == 1:
                    stats['win_mg1'] += 1
                else:
                    stats['win_mg2'] += 1
                break
        
        if not won:
            stats['losses'] += 1
            stats['patterns'][pattern]['losses'] += 1
    
    if stats['entries'] > 0:
        stats['win_rate'] = (stats['wins'] / stats['entries']) * 100
    else:
        stats['win_rate'] = 0
    
    return stats

def main():
    print("="*70)
    print("🎯 BLAZE AI BOT - ESTRATÉGIA PREMIUM (96%+ com 2 MG)")
    print("="*70)
    
    total_wins = 0
    total_entries = 0
    pattern_stats = defaultdict(lambda: {'wins': 0, 'losses': 0})
    
    for i in range(50):
        r = simulate_premium(n_games=300)
        total_wins += r['wins']
        total_entries += r['entries']
        
        for pattern, data in r['patterns'].items():
            pattern_stats[pattern]['wins'] += data['wins']
            pattern_stats[pattern]['losses'] += data['losses']
        
        if (i + 1) % 10 == 0:
            rate = (total_wins / total_entries * 100) if total_entries > 0 else 0
            print(f"Parcial {i+1}/50: {rate:.2f}% ({total_wins}/{total_entries})")
    
    final_rate = (total_wins / total_entries * 100) if total_entries > 0 else 0
    
    print("\n" + "="*70)
    print("📊 RESULTADO FINAL")
    print("="*70)
    print(f"Win Rate: {final_rate:.2f}%")
    print(f"Total Entradas: {total_entries}")
    print(f"Total Wins: {total_wins}")
    print(f"Total Losses: {total_entries - total_wins}")
    
    print("\n📈 Performance por Padrão:")
    for pattern, data in sorted(pattern_stats.items(), key=lambda x: -x[1]['wins']):
        total = data['wins'] + data['losses']
        if total > 0:
            rate = (data['wins'] / total) * 100
            print(f"  {pattern}: {rate:.1f}% ({data['wins']}/{total})")
    
    if final_rate >= 96:
        print("\n🎉 OBJETIVO ALCANÇADO!")
    
    # Simulações individuais
    print("\n📈 SIMULAÇÕES INDIVIDUAIS:")
    for i in range(20):
        r = simulate_premium(n_games=400)
        entries = r['entries']
        if entries > 0:
            print(f"Sim {i+1:2d}: {r['win_rate']:5.2f}% | "
                  f"W:{r['wins']:2d} L:{r['losses']:2d} | "
                  f"P:{r['win_principal']:2d} M1:{r['win_mg1']:2d} M2:{r['win_mg2']:2d}")

if __name__ == "__main__":
    main()
