# Blaze AI Bot - PRD (Product Requirements Document)

## Projeto
**Nome**: Blaze AI Bot  
**Versão**: 2.0  
**Data de Criação**: 31/01/2026

---

## Problema Original
Criar um robô melhorado com inteligência artificial capaz de fazer análises precisas de padrões vermelho/preto para o jogo Double (Blaze), inspirado no Bot Master Blaze mas significativamente melhorado.

---

## Arquitetura

### Backend (FastAPI + MongoDB)
- **server.py**: API REST com autenticação JWT
- **Banco**: MongoDB (collections: users, predictions, game_results, user_settings)
- **IA**: GPT-5.2 via Emergent LLM Key

### Frontend (React + Tailwind)
- **App.js**: SPA com 4 páginas (Login, Dashboard, Histórico, Estatísticas, Configurações)
- **Design**: Tema escuro premium estilo trading/cassino
- **Gráficos**: Recharts para visualização de dados

---

## Personas de Usuário

1. **Apostador Iniciante**: Busca orientação com análises claras e fáceis de entender
2. **Apostador Experiente**: Precisa de dados estatísticos e configurações avançadas
3. **Trader de Padrões**: Usa análise de IA para identificar tendências

---

## Requisitos Core (Implementados)

### Autenticação
- [x] Registro de usuário com email/senha
- [x] Login com JWT
- [x] Proteção de rotas

### Dashboard Principal
- [x] Círculos de probabilidade (vermelho/preto/branco)
- [x] Recomendação de cor com confiança
- [x] Tabela de níveis de martingale
- [x] Análise IA com GPT-5.2
- [x] Detecção de sequências e padrões
- [x] Botão "Nova Análise"

### Entrada de Dados
- [x] Adicionar resultado manual (vermelho/preto/branco)
- [x] Simulador automático em background (30s)
- [x] Histórico de últimos resultados

### Histórico
- [x] Lista de análises anteriores
- [x] Status (Win/Loss/Aguardando)
- [x] Resultado real vs recomendado

### Estatísticas
- [x] Total de análises
- [x] Wins/Losses
- [x] Taxa de acerto
- [x] Gráfico de desempenho (7 dias)
- [x] Barra de progresso

### Configurações
- [x] Máximo de martingales (1-5)
- [x] Probabilidade mínima (50-90%)
- [x] Notificações push
- [x] Sons

---

## O Que Foi Implementado

| Feature | Status | Data |
|---------|--------|------|
| Sistema de autenticação JWT | ✅ | 31/01/2026 |
| Análise IA com GPT-5.2 | ✅ | 31/01/2026 |
| Círculos de probabilidade animados | ✅ | 31/01/2026 |
| Tabela de martingales | ✅ | 31/01/2026 |
| Histórico com status Win/Loss | ✅ | 31/01/2026 |
| Estatísticas com gráficos | ✅ | 31/01/2026 |
| Configurações persistentes | ✅ | 31/01/2026 |
| Simulador em background | ✅ | 31/01/2026 |
| Design dark premium | ✅ | 31/01/2026 |
| Responsivo mobile | ✅ | 31/01/2026 |

---

## Backlog Priorizado

### P0 (Crítico) - Implementado
- Análise de padrões com IA ✅
- Dashboard funcional ✅
- Autenticação ✅

### P1 (Alta Prioridade) - Futuro
- [ ] Integração com API real da Blaze (websocket)
- [ ] Notificações push reais (Firebase/OneSignal)
- [ ] Alertas sonoros configuráveis

### P2 (Média Prioridade) - Futuro
- [ ] Sistema de backtesting com histórico real
- [ ] Múltiplas estratégias de análise
- [ ] Exportar relatórios PDF
- [ ] Modo demo sem autenticação

### P3 (Baixa Prioridade) - Futuro
- [ ] App mobile nativo
- [ ] Telegram bot integration
- [ ] Sistema de planos/assinatura

---

## Próximos Passos

1. **Integração Real**: Conectar com API de resultados em tempo real da Blaze
2. **Notificações**: Implementar push notifications com Firebase
3. **Backtesting**: Adicionar modo de teste com dados históricos
4. **Telegram**: Bot para receber sinais via Telegram

---

## Notas Técnicas

- **Emergent LLM Key**: `sk-emergent-7DfAaA78fC7A6426c4`
- **Modelo IA**: GPT-5.2 (OpenAI via emergentintegrations)
- **Porta Backend**: 8001
- **Porta Frontend**: 3000
- **Database**: MongoDB local

---

## Aviso Legal
As recomendações são baseadas em análise estatística e IA, mas não garantem resultados. Apostas envolvem riscos financeiros. Use com responsabilidade.
