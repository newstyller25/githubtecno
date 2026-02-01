"""
Blaze AI Bot - Sistema de Backtesting e Otimização
Objetivo: Atingir 96%+ de assertividade com Martingale

Este script simula milhares de jogadas do Double usando probabilidades reais
e testa todas as estratégias para encontrar a combinação ideal.
"""

import random
import json
from collections import defaultdict
from typing import List, Dict, Tuple
import statistics

# Probabilidades reais do Double Blaze
# Vermelho: 1-7 (7 números) = 46.67%
# Preto: 8-14 (7 números) = 46.67%
# Branco: 0 (1 número) = 6.67%

PROB_RED = 0.4667
PROB_BLACK = 0.4667
PROB_WHITE = 0.0666

def generate_blaze_result() -> str:
    """Gera um resultado simulando o Double da Blaze"""
    rand = random.random()
    if rand < PROB_RED:
        return 'red'
    elif rand < PROB_RED + PROB_BLACK:
        return 'black'
    else:
        return 'white'

def generate_history(n: int) -> List[str]:
    """Gera histórico de n jogadas"""
    return [generate_blaze_result() for _ in range(n)]

# ==================== ESTRATÉGIAS OTIMIZADAS ====================

def strategy_tendencia_v2(history: List[str], lookback: int = 15) -> Tuple[str, float]:
    """Estratégia: Seguir tendência com lookback otimizado"""
    if len(history) < lookback:
        return 'red', 50
    
    recent = history[-lookback:]
    red_count = recent.count('red')
    black_count = recent.count('black')
    
    # Só apostar se tendência for clara (60%+ de uma cor)
    total = red_count + black_count
    if total == 0:
        return 'red', 50
    
    red_pct = red_count / total
    
    if red_pct >= 0.60:
        confidence = 50 + (red_pct - 0.5) * 80
        return 'red', min(confidence, 90)
    elif red_pct <= 0.40:
        confidence = 50 + (0.5 - red_pct) * 80
        return 'black', min(confidence, 90)
    
    # Tendência não clara - usar estatística
    return 'red' if red_count >= black_count else 'black', 55

def strategy_reversao_v2(history: List[str], min_streak: int = 4) -> Tuple[str, float]:
    """Estratégia: Reversão após sequência longa (otimizada)"""
    if len(history) < 5:
        return 'red', 50
    
    # Contar sequência atual
    last_color = history[-1]
    if last_color == 'white':
        return 'red', 55  # Após branco, estatisticamente neutro
    
    streak = 1
    for c in reversed(history[:-1]):
        if c == last_color and c != 'white':
            streak += 1
        else:
            break
    
    # Reversão só faz sentido após sequência longa
    if streak >= min_streak:
        opposite = 'black' if last_color == 'red' else 'red'
        # Confiança aumenta com o tamanho da sequência
        # Mas não linearmente - há um limite estatístico
        confidence = 60 + min((streak - min_streak) * 5, 25)
        return opposite, confidence
    
    return 'red', 50

def strategy_padrao_duplo(history: List[str]) -> Tuple[str, float]:
    """Estratégia: Detecta padrões de 2-2 ou 3-3"""
    if len(history) < 6:
        return 'red', 50
    
    last_6 = history[-6:]
    
    # Detectar padrão 2-2 (dois de cada alternando)
    if (last_6[0] == last_6[1] and 
        last_6[2] == last_6[3] and 
        last_6[4] == last_6[5] and
        last_6[0] != last_6[2] and last_6[2] != last_6[4]):
        # Padrão 2-2 detectado, próximo deve ser oposto aos últimos 2
        opposite = 'black' if last_6[-1] == 'red' else 'red'
        return opposite, 72
    
    # Detectar padrão 3-3
    last_9 = history[-9:] if len(history) >= 9 else history
    if len(last_9) >= 9:
        if (last_9[0] == last_9[1] == last_9[2] and
            last_9[3] == last_9[4] == last_9[5] and
            last_9[6] == last_9[7] == last_9[8] and
            last_9[0] != last_9[3] and last_9[3] != last_9[6]):
            opposite = 'black' if last_9[-1] == 'red' else 'red'
            return opposite, 75
    
    return 'red', 50

def strategy_equilibrio_forcado(history: List[str], window: int = 30) -> Tuple[str, float]:
    """Estratégia: Lei dos grandes números - equilíbrio forçado"""
    if len(history) < window:
        return 'red', 50
    
    recent = history[-window:]
    red_count = recent.count('red')
    black_count = recent.count('black')
    total = red_count + black_count
    
    if total == 0:
        return 'red', 50
    
    # Probabilidade esperada: 50% cada (excluindo branco)
    expected = total / 2
    
    red_deviation = red_count - expected
    black_deviation = black_count - expected
    
    # Se desvio for significativo (> 5), apostar na correção
    if red_deviation > 5:
        confidence = 55 + min(red_deviation * 2, 30)
        return 'black', confidence
    elif black_deviation > 5:
        confidence = 55 + min(black_deviation * 2, 30)
        return 'red', confidence
    
    return 'red', 50

def strategy_anti_padrao(history: List[str]) -> Tuple[str, float]:
    """Estratégia: Detecta quando NÃO apostar (filtro)"""
    if len(history) < 10:
        return 'skip', 0
    
    last_10 = history[-10:]
    red_count = last_10.count('red')
    black_count = last_10.count('black')
    white_count = last_10.count('white')
    
    # Se houve muito branco recente, mercado instável
    if white_count >= 2:
        return 'skip', 0
    
    # Se perfeitamente equilibrado, não apostar
    if abs(red_count - black_count) <= 1:
        return 'skip', 0
    
    return 'continue', 100

def strategy_momentum(history: List[str]) -> Tuple[str, float]:
    """Estratégia: Momentum - acelerar na sequência vencedora"""
    if len(history) < 8:
        return 'red', 50
    
    # Últimas 3 jogadas
    last_3 = history[-3:]
    
    # Se as últimas 3 foram da mesma cor, continuar
    if last_3[0] == last_3[1] == last_3[2] and last_3[0] != 'white':
        return last_3[0], 68
    
    # Se alternando perfeitamente
    if last_3[0] != last_3[1] != last_3[2]:
        opposite = 'black' if last_3[-1] == 'red' else 'red'
        return opposite, 65
    
    return 'red', 50

def combined_strategy_v2(history: List[str]) -> Tuple[str, float, str]:
    """
    Estratégia combinada otimizada para 96%+ com Martingale
    Retorna: (cor, confiança, estratégia_usada)
    """
    if len(history) < 10:
        return 'red', 50, 'default'
    
    # Primeiro verificar se devemos pular
    anti = strategy_anti_padrao(history)
    if anti[0] == 'skip':
        # Em caso de skip, usar estratégia mais conservadora
        return strategy_equilibrio_forcado(history, 30)[0], 55, 'equilibrio_conservador'
    
    # Coletar votos de todas as estratégias
    strategies = {
        'tendencia': strategy_tendencia_v2(history, 15),
        'reversao': strategy_reversao_v2(history, 4),
        'padrao_duplo': strategy_padrao_duplo(history),
        'equilibrio': strategy_equilibrio_forcado(history, 30),
        'momentum': strategy_momentum(history)
    }
    
    # Sistema de votação ponderada
    votes = {'red': 0, 'black': 0}
    weights = {
        'tendencia': 1.2,
        'reversao': 1.5,  # Maior peso - mais confiável
        'padrao_duplo': 1.8,  # Maior peso quando detecta padrão
        'equilibrio': 1.0,
        'momentum': 1.1
    }
    
    best_confidence = 0
    best_strategy = 'combined'
    
    for name, (color, confidence) in strategies.items():
        if color in ['red', 'black']:
            weight = weights[name]
            vote_power = (confidence / 100) * weight
            votes[color] += vote_power
            
            # Track melhor estratégia individual
            if confidence > best_confidence:
                best_confidence = confidence
                best_strategy = name
    
    # Decisão final
    total_votes = votes['red'] + votes['black']
    if total_votes == 0:
        return 'red', 50, 'default'
    
    red_pct = votes['red'] / total_votes
    
    # Só apostar se houver consenso (>60% dos votos)
    if red_pct >= 0.60:
        final_confidence = 50 + (red_pct - 0.5) * 80
        return 'red', min(final_confidence, 92), best_strategy
    elif red_pct <= 0.40:
        final_confidence = 50 + (0.5 - red_pct) * 80
        return 'black', min(final_confidence, 92), best_strategy
    
    # Sem consenso - usar estratégia com maior confiança
    if best_confidence >= 65:
        color = strategies[best_strategy][0]
        return color, best_confidence, best_strategy
    
    # Última opção: não apostar forte
    return 'red' if votes['red'] >= votes['black'] else 'black', 55, 'low_confidence'

def simulate_with_martingale(n_games: int = 1000, max_mg: int = 2, min_confidence: int = 65) -> Dict:
    """
    Simula jogadas com sistema de Martingale
    Com Martingale, consideramos WIN se acertamos em qualquer uma das entradas
    """
    history = generate_history(50)  # Histórico inicial
    
    results = {
        'total_entries': 0,
        'wins': 0,
        'losses': 0,
        'win_at_principal': 0,
        'win_at_mg1': 0,
        'win_at_mg2': 0,
        'skipped': 0,
        'strategies_used': defaultdict(int),
        'confidence_levels': []
    }
    
    i = 0
    while i < n_games:
        # Gerar previsão
        predicted_color, confidence, strategy = combined_strategy_v2(history)
        
        # Só entrar se confiança >= mínimo
        if confidence < min_confidence:
            # Gerar resultado e adicionar ao histórico
            actual = generate_blaze_result()
            history.append(actual)
            results['skipped'] += 1
            i += 1
            continue
        
        results['total_entries'] += 1
        results['strategies_used'][strategy] += 1
        results['confidence_levels'].append(confidence)
        
        # Simular entrada principal + martingales
        won = False
        mg_level = 0
        
        for mg in range(max_mg + 1):  # 0 = principal, 1 = mg1, 2 = mg2
            actual = generate_blaze_result()
            history.append(actual)
            
            if actual == predicted_color:
                won = True
                mg_level = mg
                break
        
        if won:
            results['wins'] += 1
            if mg_level == 0:
                results['win_at_principal'] += 1
            elif mg_level == 1:
                results['win_at_mg1'] += 1
            else:
                results['win_at_mg2'] += 1
        else:
            results['losses'] += 1
        
        i += 1
    
    # Calcular métricas
    if results['total_entries'] > 0:
        results['win_rate'] = (results['wins'] / results['total_entries']) * 100
        results['principal_rate'] = (results['win_at_principal'] / results['total_entries']) * 100
        results['avg_confidence'] = statistics.mean(results['confidence_levels'])
    else:
        results['win_rate'] = 0
        results['principal_rate'] = 0
        results['avg_confidence'] = 0
    
    return results

def optimize_parameters() -> Dict:
    """Encontra os melhores parâmetros para 96%+ de win rate"""
    print("🔍 Iniciando otimização de parâmetros...\n")
    
    best_result = None
    best_win_rate = 0
    
    # Testar diferentes combinações
    for max_mg in [1, 2, 3]:
        for min_conf in [60, 65, 70, 75, 80]:
            print(f"Testando: max_mg={max_mg}, min_conf={min_conf}...")
            
            # Rodar múltiplas simulações para média
            win_rates = []
            for _ in range(5):
                result = simulate_with_martingale(
                    n_games=500,
                    max_mg=max_mg,
                    min_confidence=min_conf
                )
                win_rates.append(result['win_rate'])
            
            avg_win_rate = statistics.mean(win_rates)
            print(f"  → Win Rate médio: {avg_win_rate:.2f}%")
            
            if avg_win_rate > best_win_rate:
                best_win_rate = avg_win_rate
                best_result = {
                    'max_martingales': max_mg,
                    'min_confidence': min_conf,
                    'win_rate': avg_win_rate
                }
    
    return best_result

def run_full_test(n_simulations: int = 10, games_per_sim: int = 500) -> Dict:
    """Roda teste completo com os melhores parâmetros"""
    print("\n" + "="*60)
    print("🎯 TESTE COMPLETO DO SISTEMA BLAZE AI BOT")
    print("="*60 + "\n")
    
    # Parâmetros otimizados
    MAX_MG = 2
    MIN_CONF = 70
    
    all_results = []
    total_wins = 0
    total_losses = 0
    total_entries = 0
    
    for sim in range(n_simulations):
        result = simulate_with_martingale(
            n_games=games_per_sim,
            max_mg=MAX_MG,
            min_confidence=MIN_CONF
        )
        all_results.append(result)
        total_wins += result['wins']
        total_losses += result['losses']
        total_entries += result['total_entries']
        
        print(f"Simulação {sim+1}/{n_simulations}: {result['win_rate']:.2f}% ({result['wins']}/{result['total_entries']})")
    
    # Resultados finais
    final_win_rate = (total_wins / total_entries) * 100 if total_entries > 0 else 0
    
    print("\n" + "="*60)
    print("📊 RESULTADOS FINAIS")
    print("="*60)
    print(f"Total de entradas: {total_entries}")
    print(f"Wins: {total_wins}")
    print(f"Losses: {total_losses}")
    print(f"Win Rate: {final_win_rate:.2f}%")
    print(f"Parâmetros: max_mg={MAX_MG}, min_conf={MIN_CONF}")
    
    # Análise por estratégia
    print("\n📈 Estratégias mais usadas:")
    strategy_totals = defaultdict(int)
    for r in all_results:
        for s, count in r['strategies_used'].items():
            strategy_totals[s] += count
    
    for strategy, count in sorted(strategy_totals.items(), key=lambda x: -x[1])[:5]:
        print(f"  - {strategy}: {count} entradas")
    
    return {
        'total_entries': total_entries,
        'total_wins': total_wins,
        'total_losses': total_losses,
        'win_rate': final_win_rate,
        'parameters': {'max_mg': MAX_MG, 'min_conf': MIN_CONF}
    }

if __name__ == "__main__":
    # Primeiro otimizar parâmetros
    print("🚀 Sistema de Backtesting Blaze AI Bot")
    print("Objetivo: Atingir 96%+ de assertividade com Martingale\n")
    
    # Teste rápido
    print("📊 Teste inicial...")
    result = simulate_with_martingale(n_games=1000, max_mg=2, min_confidence=70)
    print(f"Win Rate: {result['win_rate']:.2f}%")
    print(f"Principal: {result['principal_rate']:.2f}%")
    print(f"Entradas: {result['total_entries']}")
    print(f"Skipped: {result['skipped']}")
    
    # Otimização
    print("\n" + "="*60)
    best = optimize_parameters()
    print(f"\n✅ Melhores parâmetros encontrados:")
    print(f"   max_martingales: {best['max_martingales']}")
    print(f"   min_confidence: {best['min_confidence']}")
    print(f"   win_rate: {best['win_rate']:.2f}%")
    
    # Teste completo final
    final = run_full_test(n_simulations=10, games_per_sim=500)
    
    print("\n" + "="*60)
    if final['win_rate'] >= 96:
        print("🎉 OBJETIVO ALCANÇADO! Win rate >= 96%")
    else:
        print(f"⚠️ Win rate atual: {final['win_rate']:.2f}%")
        print("   Ajustes necessários para atingir 96%")
