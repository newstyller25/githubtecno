# Blaze AI Bot - PRD v2.0 (Atualizado)

## Projeto
**Nome**: Blaze AI Bot  
**Versão**: 2.1 - Sistema Adaptativo  
**Data**: 01/02/2026

---

## Problema Original
Criar um robô com IA para análise de padrões vermelho/preto que:
- Faça análises precisas
- Após LOSS, pare, reanalisar e mude de estratégia
- Melhore a precisão continuamente

---

## Sistema de Múltiplas Estratégias (NOVO)

### Estratégias Implementadas
1. **Seguir Tendência** - Aposta na cor dominante recente
2. **Reversão à Média** - Aposta na cor oposta após sequências longas
3. **Padrão Alternado** - Detecta e segue alternâncias entre cores
4. **Sequência Fibonacci** - Usa intervalos de Fibonacci para ciclos
5. **Análise Estatística Pura** - Probabilidades matemáticas
6. **IA Análise Profunda** - GPT-5.2 analisa padrões complexos

### Sistema de Votação
- Todas as estratégias rodam em paralelo
- Cada uma "vota" em uma cor com peso baseado na confiança
- Resultado final combina estratégia principal + votação

### Aprendizado Adaptativo
- Após cada LOSS:
  1. Sistema detecta automaticamente
  2. Analisa performance de cada estratégia
  3. Muda para estratégia com melhor win rate
  4. Penaliza estratégias com muitos losses recentes

---

## Features Implementadas

| Feature | Status |
|---------|--------|
| Análise IA GPT-5.2 | ✅ |
| 6 Estratégias de análise | ✅ |
| Sistema de votação | ✅ |
| Detecção automática de LOSS | ✅ |
| Mudança automática de estratégia | ✅ |
| Tracking de performance por estratégia | ✅ |
| Dashboard com análise detalhada | ✅ |
| Histórico de WIN/LOSS | ✅ |
| Configurações personalizáveis | ✅ |
| WebSocket tempo real | ✅ |

---

## Como Funciona o Sistema Adaptativo

```
1. Usuário solicita análise
   ↓
2. Sistema executa TODAS as 6 estratégias
   ↓
3. Cada estratégia "vota" em uma cor
   ↓
4. Sistema combina votos + estratégia principal
   ↓
5. Gera recomendação final
   ↓
6. Após resultado real:
   - WIN: Incrementa score da estratégia
   - LOSS: Detecta, reanalisar, muda estratégia
```

---

## Credenciais de Teste
- **Email**: test@blaze.com
- **Senha**: test123

---

## Próximos Passos

### P0 (Prioridade)
- [ ] Conectar com API real da Blaze (WebSocket)
- [ ] Melhorar detecção de padrões

### P1 
- [ ] Bot Telegram para sinais
- [ ] Notificações push
- [ ] Backtesting com dados históricos

---

## Notas Técnicas
- **IA**: GPT-5.2 via Emergent LLM Key
- **6 Estratégias** rodando em paralelo
- **Sistema de votação** para maior precisão
- **Auto-ajuste** após cada LOSS
