"""
Blaze Scraper - Captura resultados em tempo real do BestBlaze
"""

import asyncio
import aiohttp
from bs4 import BeautifulSoup
import re
from datetime import datetime, timezone
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BESTBLAZE_URL = "https://www.bestblaze.com.br/index"

class BlazeScraper:
    def __init__(self, backend_url: str = "http://localhost:8001"):
        self.backend_url = backend_url
        self.last_result_time = None
        self.last_results = []
        self.running = False
    
    def parse_color(self, class_name: str) -> str:
        """Converte classe CSS para cor"""
        if 'Vrodada' in class_name:
            return 'red'
        elif 'Prodada' in class_name:
            return 'black'
        elif 'Brodada' in class_name:
            return 'white'
        return None
    
    def parse_roll(self, number_str: str) -> int:
        """Converte número string para int"""
        try:
            return int(number_str.strip())
        except:
            return -1
    
    async def fetch_results(self) -> list:
        """Faz scraping dos resultados do BestBlaze"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(BESTBLAZE_URL, timeout=10) as response:
                    if response.status != 200:
                        logger.error(f"Erro ao acessar BestBlaze: {response.status}")
                        return []
                    
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    results = []
                    
                    # Encontrar todos os elementos com resultados
                    rodadas = soup.select('.numeroRodadas')
                    
                    for rodada in rodadas:
                        classes = rodada.get('class', [])
                        class_str = ' '.join(classes) if isinstance(classes, list) else classes
                        
                        color = self.parse_color(class_str)
                        if not color:
                            continue
                        
                        # Extrair número
                        num_el = rodada.select_one('.num')
                        if not num_el:
                            continue
                        
                        number = self.parse_roll(num_el.get_text())
                        if number < 0:
                            continue
                        
                        # Extrair horário
                        time_el = rodada.select_one('.time, .timeDouble')
                        time_str = time_el.get_text().strip() if time_el else ""
                        
                        results.append({
                            'color': color,
                            'roll': number,
                            'time': time_str,
                            'timestamp': datetime.now(timezone.utc).isoformat()
                        })
                    
                    return results
                    
        except Exception as e:
            logger.error(f"Erro no scraping: {e}")
            return []
    
    async def send_to_backend(self, result: dict):
        """Envia resultado para o backend"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.backend_url}/api/blaze/result",
                    json=result,
                    timeout=5
                ) as response:
                    if response.status == 200:
                        logger.info(f"✅ Enviado: {result['color'].upper()} (roll: {result['roll']})")
                    else:
                        logger.error(f"Erro ao enviar: {response.status}")
        except Exception as e:
            logger.error(f"Erro ao enviar para backend: {e}")
    
    async def run(self, interval: int = 5):
        """Loop principal de scraping"""
        self.running = True
        logger.info(f"🚀 Iniciando scraper BestBlaze (intervalo: {interval}s)")
        
        while self.running:
            try:
                results = await self.fetch_results()
                
                if results:
                    # Pegar o resultado mais recente
                    latest = results[0]
                    
                    # Verificar se é novo (comparar com último enviado)
                    is_new = True
                    if self.last_results:
                        last = self.last_results[0]
                        if (last['roll'] == latest['roll'] and 
                            last['time'] == latest['time']):
                            is_new = False
                    
                    if is_new:
                        logger.info(f"🎰 Novo resultado: {latest['color'].upper()} (roll: {latest['roll']}) às {latest['time']}")
                        await self.send_to_backend(latest)
                        self.last_results = results
                
                await asyncio.sleep(interval)
                
            except Exception as e:
                logger.error(f"Erro no loop: {e}")
                await asyncio.sleep(interval)
    
    def stop(self):
        """Para o scraper"""
        self.running = False
        logger.info("🛑 Scraper parado")


async def main():
    scraper = BlazeScraper()
    
    try:
        await scraper.run(interval=3)  # Verificar a cada 3 segundos
    except KeyboardInterrupt:
        scraper.stop()


if __name__ == "__main__":
    asyncio.run(main())
