/**
 * Blaze Double Connector - Tempo Real
 * Conecta ao WebSocket da Blaze e envia resultados para o backend
 */

const { io } = require('socket.io-client');
const axios = require('axios');

// Configurações
const BLAZE_WS_URL = 'wss://api-v2.blaze.com';
const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8001';

// Estado
let lastResult = null;
let history = [];
let connected = false;
let reconnectAttempts = 0;

// Cores baseadas no roll
function getColor(roll) {
    if (roll === 0) return 'white';
    if (roll >= 1 && roll <= 7) return 'red';
    return 'black'; // 8-14
}

// Enviar resultado para o backend
async function sendToBackend(result) {
    try {
        await axios.post(`${BACKEND_URL}/api/blaze/result`, result, {
            headers: { 'Content-Type': 'application/json' }
        });
        console.log(`✅ Enviado para backend: ${result.color.toUpperCase()} (roll: ${result.roll})`);
    } catch (error) {
        console.error('❌ Erro ao enviar para backend:', error.message);
    }
}

// Conectar ao WebSocket da Blaze
function connectToBlaze() {
    console.log('🔌 Conectando ao WebSocket da Blaze...');
    
    const socket = io(BLAZE_WS_URL, {
        transports: ['websocket'],
        upgrade: false,
        reconnection: true,
        reconnectionAttempts: Infinity,
        reconnectionDelay: 1000,
        reconnectionDelayMax: 5000,
        extraHeaders: {
            'Origin': 'https://blaze.com',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
    });

    socket.on('connect', () => {
        connected = true;
        reconnectAttempts = 0;
        console.log('✅ Conectado ao WebSocket da Blaze!');
        
        // Subscrever ao canal do Double
        socket.emit('cmd', {
            id: 'subscribe',
            payload: { room: 'double_v2' }
        });
        console.log('📡 Inscrito no canal double_v2');
    });

    socket.on('disconnect', (reason) => {
        connected = false;
        console.log(`❌ Desconectado: ${reason}`);
    });

    socket.on('connect_error', (error) => {
        reconnectAttempts++;
        console.log(`⚠️ Erro de conexão (tentativa ${reconnectAttempts}): ${error.message}`);
    });

    // Evento principal - tick do Double
    socket.on('double.tick', (data) => {
        if (data && data.status === 'complete' && data.roll !== undefined) {
            const color = getColor(data.roll);
            
            const result = {
                color: color,
                roll: data.roll,
                id: data.id,
                timestamp: new Date().toISOString(),
                server_seed: data.server_seed
            };
            
            // Evitar duplicatas
            if (!lastResult || lastResult.id !== result.id) {
                lastResult = result;
                history.unshift(result);
                history = history.slice(0, 100); // Manter últimos 100
                
                console.log(`🎰 Novo resultado: ${color.toUpperCase()} (roll: ${data.roll})`);
                
                // Enviar para backend
                sendToBackend(result);
            }
        }
        
        // Log de status
        if (data && data.status) {
            if (data.status === 'waiting') {
                console.log('⏳ Aguardando próxima rodada...');
            } else if (data.status === 'rolling') {
                console.log('🎰 Girando...');
            }
        }
    });

    return socket;
}

// Status endpoint
const http = require('http');
const server = http.createServer((req, res) => {
    if (req.url === '/status') {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({
            connected: connected,
            lastResult: lastResult,
            historyCount: history.length,
            recentHistory: history.slice(0, 10)
        }));
    } else if (req.url === '/history') {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(history));
    } else {
        res.writeHead(404);
        res.end('Not Found');
    }
});

// Iniciar
console.log('🚀 Blaze Connector iniciando...');
console.log(`📡 Backend URL: ${BACKEND_URL}`);

const socket = connectToBlaze();

server.listen(3001, () => {
    console.log('🌐 Status server rodando em http://localhost:3001');
});

// Graceful shutdown
process.on('SIGINT', () => {
    console.log('\n👋 Encerrando...');
    socket.disconnect();
    server.close();
    process.exit(0);
});
