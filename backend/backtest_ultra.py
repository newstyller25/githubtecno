"""
Blaze AI Bot - Estratégias ULTRA para 96%+ com apenas 2 Martingales
Requer filtros extremamente rigorosos
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

# ==================== FILTROS ULTRA-RIGOROSOS ====================

def ultra_filter(colors: List[str]) -> Tuple[bool, str]:
    """Filtro EXTREMAMENTE rigoroso para 96%+ com 2 MG"""
    if len(colors) < 30:
        return True, "histórico_insuficiente"
    
    last_30 = colors[-30:]
    last_20 = colors[-20:]
    last_10 = colors[-10:]
    last_5 = colors[-5:]
    
    # 1. Qualquer branco nas últimas 15 = SKIP
    white_15 = colors[-15:].count('white')
    if white_15 >= 1:
        return True, "branco_recente"
    
    # 2. Equilibrado nas últimas 20 = SKIP
    red_20 = last_20.count('red')
    black_20 = last_20.count('black')
    total_20 = red_20 + black_20
    if total_20 > 0:
        balance = abs(red_20 - black_20) / total_20
        if balance < 0.20:  # Precisa de pelo menos 20% de diferença
            return True, "equilibrado"
    
    # 3. Muitas mudanças = mercado caótico = SKIP
    changes_20 = sum(1 for i in range(len(last_20)-1) if last_20[i] != last_20[i+1])
    if changes_20 >= 13:  # Mais de 65% de mudanças
        return True, "caótico"
    
    # 4. Sequência > 5 = SKIP (reversão imprevisível)
    non_white = [c for c in colors if c != 'white']
    streak = 1
    if non_white:
        last = non_white[-1]
        for c in reversed(non_white[:-1]):
            if c == last:
                streak += 1
            else:
                break
    if streak >= 6:
        return True, "sequência_longa"
    
    # 5. Alternância perfeita nas últimas 8 = SKIP
    nw_10 = [c for c in last_10 if c != 'white']
    if len(nw_10) >= 7:
        alt = all(nw_10[i] != nw_10[i+1] for i in range(len(nw_10)-1))
        if alt:
            return True, "alternância_perfeita"
    
    # 6. Verificar consistência de tendência em múltiplos timeframes
    red_5 = last_5.count('red')
    red_10 = last_10.count('red')
    
    # Se tendência recente contradiz tendência média = SKIP
    trend_5 = 'red' if red_5 >= 3 else ('black' if red_5 <= 2 else 'neutral')
    trend_10 = 'red' if red_10 >= 6 else ('black' if red_10 <= 4 else 'neutral')
    trend_20 = 'red' if red_20 >= 11 else ('black' if red_20 <= 9 else 'neutral')
    
    if trend_5 != 'neutral' and trend_10 != 'neutral' and trend_5 != trend_10:
        return True, "tendência_contraditória"
    
    return False, "ok"

# ==================== ESTRATÉGIAS ULTRA ====================

def ultra_trend(colors: List[str]) -> Tuple[str, float]:
    """Tendência com confirmação múltipla"""
    if len(colors) < 50:
        return 'skip', 0
    
    def get_ratio(n):
        subset = [c for c in colors[-n:] if c != 'white']
        return subset.count('red') / len(subset) if subset else 0.5
    
    r5 = get_ratio(5)
    r10 = get_ratio(10)
    r20 = get_ratio(20)
    r30 = get_ratio(30)
    r50 = get_ratio(50)
    
    # Score ponderado com mais peso para recente
    score = r5 * 0.35 + r10 * 0.25 + r20 * 0.20 + r30 * 0.12 + r50 * 0.08
    
    # ULTRA exigente: só apostar se score >= 0.65 ou <= 0.35
    if score >= 0.65:
        # Verificar se TODOS os timeframes concordam
        if r5 >= 0.6 and r10 >= 0.55 and r20 >= 0.52:
            confidence = 70 + (score - 0.5) * 100
            return 'red', min(confidence, 92)
    elif score <= 0.35:
        if r5 <= 0.4 and r10 <= 0.45 and r20 <= 0.48:
            confidence = 70 + (0.5 - score) * 100
            return 'black', min(confidence, 92)
    
    return 'skip', 0

def ultra_reversal(colors: List[str]) -> Tuple[str, float]:
    """Reversão ULTRA conservadora"""
    if len(colors) < 20:
        return 'skip', 0
    
    non_white = [c for c in colors if c != 'white']
    if len(non_white) < 15:
        return 'skip', 0
    
    # Contar sequência
    last = non_white[-1]
    streak = 1
    for c in reversed(non_white[:-1]):
        if c == last:
            streak += 1
        else:
            break
    
    # Só apostar em reversão após sequência de EXATAMENTE 4 ou 5
    # (6+ é muito arriscado, < 4 não tem edge suficiente)
    if streak in [4, 5]:
        opposite = 'black' if last == 'red' else 'red'
        
        # Verificar se a cor oposta está "devendo" muito
        last_40 = [c for c in colors[-40:] if c != 'white']
        if last_40:
            opposite_ratio = last_40.count(opposite) / len(last_40)
            
            # Só apostar se cor oposta < 42% (muito abaixo da média)
            if opposite_ratio < 0.42:
                confidence = 72 + (streak - 4) * 5 + (0.5 - opposite_ratio) * 50
                return opposite, min(confidence, 90)
    
    return 'skip', 0

def ultra_pattern(colors: List[str]) -> Tuple[str, float]:
    """Padrões ULTRA específicos"""
    if len(colors) < 15:
        return 'skip', 0
    
    non_white = [c for c in colors[-15:] if c != 'white']
    if len(non_white) < 10:
        return 'skip', 0
    
    # Padrão 2-2-2 (mais confiável)
    if len(non_white) >= 8:
        last_8 = non_white[-8:]
        # Verificar padrão AABBCCDD
        if (last_8[0] == last_8[1] and 
            last_8[2] == last_8[3] and
            last_8[4] == last_8[5] and
            last_8[6] == last_8[7] and
            last_8[0] != last_8[2] and 
            last_8[2] != last_8[4] and 
            last_8[4] != last_8[6]):
            # Próximo par deve ser diferente
            next_color = 'red' if last_8[7] == 'black' else 'black'
            return next_color, 85
    
    # Padrão 3-3 (também confiável)
    if len(non_white) >= 9:
        last_9 = non_white[-9:]
        if (last_9[0] == last_9[1] == last_9[2] and
            last_9[3] == last_9[4] == last_9[5] and
            last_9[6] == last_9[7] == last_9[8] and
            last_9[0] != last_9[3] and last_9[3] != last_9[6]):
            next_color = 'red' if last_9[8] == 'black' else 'black'
            return next_color, 88
    
    return 'skip', 0

def ultra_combined(colors: List[str]) -> Tuple[str, float, str, bool]:
    """Combinação ULTRA para 96%+ com 2 MG"""
    
    # Filtro ULTRA rigoroso
    skip, reason = ultra_filter(colors)
    if skip:
        return 'skip', 0, reason, False
    
    # Coletar análises
    results = {
        'trend': ultra_trend(colors),
        'reversal': ultra_reversal(colors),
        'pattern': ultra_pattern(colors)
    }
    
    # Pesos (padrões têm mais peso pois são mais confiáveis)
    weights = {'trend': 1.0, 'reversal': 1.3, 'pattern': 2.0}
    
    # Contagem de votos
    votes = {'red': 0, 'black': 0}
    valid_strategies = []
    best = ('skip', 0, 'none')
    
    for name, (color, conf) in results.items():
        if color in ['red', 'black'] and conf >= 70:  # Mínimo 70%
            w = weights[name]
            votes[color] += (conf / 100) * w
            valid_strategies.append((name, color, conf))
            if conf > best[1]:
                best = (color, conf, name)
    
    # Sem estratégias válidas = SKIP
    if not valid_strategies:
        return 'skip', 0, 'sem_sinal_forte', False
    
    # Verificar consenso ULTRA alto
    total = votes['red'] + votes['black']
    if total == 0:
        return 'skip', 0, 'sem_votos', False
    
    red_ratio = votes['red'] / total
    
    # Para 96%+ com 2 MG, precisamos de consenso >= 75%
    if red_ratio >= 0.75:
        # Verificar se pelo menos 2 estratégias concordam
        red_strategies = sum(1 for _, c, _ in valid_strategies if c == 'red')
        if red_strategies >= 2 or best[1] >= 85:
            avg_conf = statistics.mean([c for _, _, c in valid_strategies if _ in ['red', 'black']])
            return 'red', min(avg_conf + 3, 95), best[2], True
    elif red_ratio <= 0.25:
        black_strategies = sum(1 for _, c, _ in valid_strategies if c == 'black')
        if black_strategies >= 2 or best[1] >= 85:
            avg_conf = statistics.mean([c for _, _, c in valid_strategies if _ in ['red', 'black']])
            return 'black', min(avg_conf + 3, 95), best[2], True
    
    # Se uma estratégia tem confiança >= 85, confiar nela
    if best[1] >= 85:
        return best[0], best[1], best[2], True
    
    return 'skip', 0, 'consenso_insuficiente', False

def simulate_ultra(n_games: int = 500) -> dict:
    """Simulação com 2 Martingales"""
    history = generate_history(100)
    
    stats = {
        'entries': 0, 'wins': 0, 'losses': 0, 'skipped': 0,
        'win_principal': 0, 'win_mg1': 0, 'win_mg2': 0,
        'strategies': defaultdict(int),
        'skip_reasons': defaultdict(int)
    }
    
    for _ in range(n_games):
        color, conf, strategy, should_enter = ultra_combined(history)
        
        if not should_enter:
            history.append(generate_result())
            stats['skipped'] += 1
            stats['skip_reasons'][strategy] += 1
            continue
        
        stats['entries'] += 1
        stats['strategies'][strategy] += 1
        
        # Simular com 2 martingales
        won = False
        for mg in range(3):  # 0=principal, 1=mg1, 2=mg2
            actual = generate_result()
            history.append(actual)
            if actual == color:
                won = True
                stats['wins'] += 1
                if mg == 0:
                    stats['win_principal'] += 1
                elif mg == 1:
                    stats['win_mg1'] += 1
                else:
                    stats['win_mg2'] += 1
                break
        
        if not won:
            stats['losses'] += 1
    
    if stats['entries'] > 0:
        stats['win_rate'] = (stats['wins'] / stats['entries']) * 100
        stats['entry_rate'] = (stats['entries'] / (stats['entries'] + stats['skipped'])) * 100
    else:
        stats['win_rate'] = 0
        stats['entry_rate'] = 0
    
    return stats

def main():
    print("="*70)
    print("🎯 BLAZE AI BOT - TESTE ULTRA PARA 96%+ COM 2 MARTINGALES")
    print("="*70)
    
    total_wins = 0
    total_entries = 0
    total_skipped = 0
    
    for i in range(30):
        r = simulate_ultra(n_games=300)
        total_wins += r['wins']
        total_entries += r['entries']
        total_skipped += r['skipped']
        
        if (i + 1) % 10 == 0:
            rate = (total_wins / total_entries * 100) if total_entries > 0 else 0
            entry_rate = (total_entries / (total_entries + total_skipped) * 100)
            print(f"Parcial {i+1}/30: {rate:.2f}% win rate | {entry_rate:.1f}% entrada")
    
    final_rate = (total_wins / total_entries * 100) if total_entries > 0 else 0
    final_entry = (total_entries / (total_entries + total_skipped) * 100)
    
    print("\n" + "="*70)
    print("📊 RESULTADO FINAL (2 MARTINGALES)")
    print("="*70)
    print(f"Win Rate: {final_rate:.2f}%")
    print(f"Taxa de Entrada: {final_entry:.1f}%")
    print(f"Entradas: {total_entries} | Skipped: {total_skipped}")
    
    if final_rate >= 96:
        print("\n🎉 OBJETIVO ALCANÇADO! 96%+ com 2 Martingales!")
    else:
        print(f"\n⚠️ Win rate atual: {final_rate:.2f}% - ajustes necessários")
    
    # Simulações detalhadas
    print("\n📈 SIMULAÇÕES DETALHADAS:")
    for i in range(15):
        r = simulate_ultra(n_games=400)
        print(f"Sim {i+1:2d}: {r['win_rate']:5.2f}% | "
              f"P:{r['win_principal']:2d} M1:{r['win_mg1']:2d} M2:{r['win_mg2']:2d} | "
              f"L:{r['losses']:2d} | Entry: {r['entry_rate']:.1f}%")

if __name__ == "__main__":
    main()
