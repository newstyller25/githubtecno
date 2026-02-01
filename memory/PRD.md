# Blaze AI Bot - PRD (Product Requirements Document)

## Projeto
**Nome**: Blaze AI Bot  
**Versão**: 2.0  
**Data**: 01/02/2026

---

## Problema Original
Criar um robô melhorado com IA para análise de padrões vermelho/preto do jogo Double (Blaze), com:
- Atualização automática de sinais
- Confirmação de WIN/LOSS em tempo real
- Integração com dados da Blaze

---

## Arquitetura

### Backend (FastAPI + MongoDB)
- **server.py**: API REST + WebSocket para tempo real
- **Banco**: MongoDB (users, predictions, game_results, user_settings)
- **IA**: GPT-5.2 via Emergent LLM Key
- **WebSocket Blaze**: Tentativa de conexão ao vivo (com fallback para simulação)

### Frontend (React + Tailwind)
- **App.js**: SPA com 4 abas (Dashboard, Histórico, Estatísticas, Configurações)
- **WebSocket**: Recebe atualizações em tempo real
- **Design**: Tema escuro premium estilo trading/cassino

---

## O Que Foi Implementado ✅

| Feature | Status | Data |
|---------|--------|------|
| Análise IA com GPT-5.2 | ✅ | 01/02/2026 |
| Círculos de probabilidade (vermelho/preto/branco) | ✅ | 01/02/2026 |
| Tabela de martingales com níveis | ✅ | 01/02/2026 |
| Análise detalhada da IA | ✅ | 01/02/2026 |
| Sistema de login/autenticação JWT | ✅ | 01/02/2026 |
| Histórico de análises com WIN/LOSS | ✅ | 01/02/2026 |
| Estatísticas com gráficos | ✅ | 01/02/2026 |
| Configurações (martingales, probabilidade, som) | ✅ | 01/02/2026 |
| WebSocket para atualizações em tempo real | ✅ | 01/02/2026 |
| Conexão WebSocket com Blaze (tentativa) | ✅ | 01/02/2026 |
| Simulador automático (fallback) | ✅ | 01/02/2026 |
| Entrada manual de resultados | ✅ | 01/02/2026 |

---

## Status da Conexão com Blaze

A conexão WebSocket direta com a Blaze (`wss://api-v2.blaze.com`) está implementada, mas pode ser bloqueada pelo servidor da Blaze por questões de autenticação/CORS.

**Modo Atual**: Simulação com possibilidade de entrada manual

**Como usar**:
1. Acompanhe o jogo Double na Blaze
2. Quando sair um resultado, clique na cor correspondente no painel
3. O sistema atualiza o WIN/LOSS automaticamente e gera nova análise

---

## Credenciais de Teste
- **Email**: test@blaze.com
- **Senha**: test123

---

## Backlog Priorizado

### P0 (Implementado)
- ✅ Análise IA com GPT-5.2
- ✅ Dashboard funcional
- ✅ Autenticação
- ✅ Entrada manual de resultados

### P1 (Alta Prioridade) - Próximos
- [ ] Usar biblioteca Node.js @viniciusgdr/Blaze em microserviço
- [ ] Notificações push com Firebase
- [ ] Alertas sonoros configuráveis

### P2 (Média Prioridade)
- [ ] Backtesting com dados históricos
- [ ] Exportar relatórios PDF
- [ ] Múltiplas estratégias

### P3 (Baixa Prioridade)
- [ ] Bot Telegram
- [ ] App mobile nativo

---

## Notas Técnicas
- **Emergent LLM Key**: sk-emergent-7DfAaA78fC7A6426c4
- **Modelo IA**: GPT-5.2 (OpenAI via emergentintegrations)
- **Portas**: Backend 8001, Frontend 3000
- **Database**: MongoDB local

---

## Aviso Legal
As análises são baseadas em IA e estatística, sem garantia de resultados. Aposte com responsabilidade.
