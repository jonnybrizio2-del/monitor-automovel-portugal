#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Monitor de Mercado Automóvel - Portugal
Rastreamento de preços para Yamaha NMAX e BMW Série 3
Plataformas: Standvirtual e OLX Portugal
"""

import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime
from pathlib import Path
import time
import random
from urllib.parse import urljoin
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Criar diretório de dados se não existir
DADOS_DIR = Path('dados')
DADOS_DIR.mkdir(exist_ok=True)
HISTORICO_DIR = DADOS_DIR / 'historico'
HISTORICO_DIR.mkdir(exist_ok=True)

# User agents variados para evitar bloqueios
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
    'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0'
]

class MonitorAutomovel:
    def __init__(self):
        self.session = requests.Session()
        self.headers = {
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'pt-PT,pt;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Cache-Control': 'max-age=0',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Referer': 'https://www.google.com/',
        }
        self.session.headers.update(self.headers)
        self.timestamp = datetime.now().isoformat()
        self.max_retries = 3
        self.retry_delay = 2
    
    def _get_with_retry(self, url, timeout=15, is_olx=False):
        """
        Faz requisição com retry automático e delays maiores para OLX
        """
        for attempt in range(self.max_retries):
            try:
                # Atualizar User-Agent a cada tentativa
                self.session.headers['User-Agent'] = random.choice(USER_AGENTS)
                
                logger.info(f"Tentativa {attempt + 1}/{self.max_retries} para: {url}")
                response = self.session.get(url, timeout=timeout, allow_redirects=True)
                response.raise_for_status()
                return response
            except requests.exceptions.RequestException as e:
                logger.warning(f"Erro na tentativa {attempt + 1}: {e}")
                if attempt < self.max_retries - 1:
                    # Delay mais longo para OLX
                    if is_olx:
                        wait_time = (self.retry_delay * (attempt + 2)) + random.uniform(3, 8)
                    else:
                        wait_time = self.retry_delay * (attempt + 1) + random.uniform(0, 2)
                    logger.info(f"Aguardando {wait_time:.1f}s antes de tentar novamente...")
                    time.sleep(wait_time)
                else:
                    raise
    
    def buscar_standvirtual(self, modelo):
        """
        Busca anúncios no Standvirtual com seletores CSS atualizados
        """
        print(f"\n🔍 Buscando '{modelo}' no Standvirtual...")
        try:
            # URLs para busca no Standvirtual
            urls_sv = {
                'Yamaha NMAX': 'https://www.standvirtual.com/anuncios/motos-scooters-ciclomotores?searchText=Yamaha+NMAX&sort_by=created_at_desc',
                'BMW Série 3': 'https://www.standvirtual.com/anuncios/automoveis?searchText=BMW+Serie+3&sort_by=created_at_desc'
            }
            
            url = urls_sv.get(modelo)
            if not url:
                print(f"⚠️ Modelo não configurado: {modelo}")
                return None
            
            response = self._get_with_retry(url)
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extrair dados do Standvirtual - seletores CSS atualizados
            anuncios = []
            
            # Procurar por elementos de anúncio (novos seletores)
            # Standvirtual usa divs com data-testid e classes específicas
            items = soup.find_all('article', {'class': lambda x: x and 'item' in x})
            
            if not items:
                items = soup.find_all('div', {'data-testid': 'listing-item'})
            
            if not items:
                items = soup.find_all('a', {'class': lambda x: x and 'link' in x})
            
            logger.info(f"Encontrados {len(items)} itens na página")
            
            for item in items[:30]:  # Limitar a 30 resultados
                try:
                    # Tentar extrair link primeiro (geralmente é o container)
                    link_elem = item.find('a', href=True)
                    if not link_elem:
                        link_elem = item if item.name == 'a' else None
                    
                    if not link_elem:
                        continue
                    
                    # Extrair título
                    titulo_elem = item.find('h2') or item.find('h3') or item.find('span', {'class': lambda x: x and 'title' in x})
                    titulo = titulo_elem.get_text(strip=True) if titulo_elem else None
                    
                    # Se não achou com seletores, tentar text direto
                    if not titulo:
                        titulo = link_elem.get_text(strip=True)[:100]
                    
                    # Extrair preço
                    preco_elem = item.find('span', {'class': lambda x: x and 'price' in x}) or \
                                 item.find('p', {'class': lambda x: x and 'price' in x}) or \
                                 item.find('strong')
                    preco = preco_elem.get_text(strip=True) if preco_elem else 'Sob consulta'
                    
                    # Extrair URL
                    url_anuncio = link_elem.get('href', '#')
                    
                    # Garantir que a URL é absoluta
                    if url_anuncio.startswith('/'):
                        url_anuncio = f"https://www.standvirtual.com{url_anuncio}"
                    elif not url_anuncio.startswith('http'):
                        url_anuncio = urljoin('https://www.standvirtual.com', url_anuncio)
                    
                    # Validar dados
                    if titulo and len(titulo) > 5 and url_anuncio.startswith('http'):
                        anuncios.append({
                            'titulo': titulo,
                            'preco': preco,
                            'url': url_anuncio
                        })
                        logger.info(f"✓ Adicionado: {titulo[:50]}... | {preco}")
                except Exception as e:
                    logger.debug(f"Erro ao processar item: {e}")
                    continue
            
            print(f"✅ {len(anuncios)} anúncios encontrados no Standvirtual")
            
            return {
                'plataforma': 'Standvirtual',
                'total_anuncios': len(anuncios),
                'anuncios': anuncios,
                'url_busca': url,
                'data_busca': self.timestamp
            }
        except Exception as e:
            print(f"❌ Erro ao buscar Standvirtual: {e}")
            logger.exception("Stack trace:")
            return None
    
    def buscar_olx(self, modelo):
        """
        Busca anúncios no OLX Portugal com delays aumentados para evitar bloqueio
        """
        print(f"🔍 Buscando '{modelo}' no OLX...")
        try:
            # URLs para busca no OLX
            urls_olx = {
                'Yamaha NMAX': 'https://www.olx.pt/search/q-yamaha-nmax/',
                'BMW Série 3': 'https://www.olx.pt/search/q-bmw-serie-3/'
            }
            
            url = urls_olx.get(modelo)
            if not url:
                print(f"⚠️ Modelo não configurado: {modelo}")
                return None
            
            # ⏸️ DELAY IMPORTANTE: OLX é mais agressivo com bloqueios
            # Usando delay entre 8-15 segundos para parecer mais humano
            delay = random.uniform(8, 15)
            logger.info(f"⏸️  Aguardando {delay:.1f}s antes de acessar OLX (anti-bot)...")
            print(f"⏸️  Aguardando {delay:.1f}s antes de acessar OLX...")
            time.sleep(delay)
            
            # Headers específicos para OLX
            headers_olx = self.headers.copy()
            headers_olx['Referer'] = 'https://www.olx.pt/'
            # Adicionar mais headers realistas
            headers_olx['Origin'] = 'https://www.olx.pt'
            headers_olx['Pragma'] = 'no-cache'
            self.session.headers.update(headers_olx)
            
            response = self._get_with_retry(url, timeout=20, is_olx=True)
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extrair dados do OLX - seletores CSS para OLX atual
            anuncios = []
            
            # Procurar por elementos de anúncio - OLX usa divs específicas
            items = soup.find_all('div', {'data-cy': 'listing-item'})
            
            if not items:
                items = soup.find_all('a', {'class': lambda x: x and 'listing' in x})
            
            if not items:
                items = soup.find_all('div', {'class': lambda x: x and 'OLXad' in x})
            
            if not items:
                # Última tentativa - procurar por links de anúncios
                items = soup.find_all('a', {'href': lambda x: x and '/anuncio/' in x})
            
            logger.info(f"Encontrados {len(items)} itens na página OLX")
            
            for item in items[:30]:  # Limitar a 30 resultados
                try:
                    # Para OLX, geralmente o item é um link ou container de link
                    if item.name == 'a':
                        link_elem = item
                    else:
                        link_elem = item.find('a', href=True)
                    
                    if not link_elem:
                        continue
                    
                    # Extrair título
                    titulo_elem = item.find('h2') or item.find('h3') or item.find('span', {'class': lambda x: x and 'title' in x})
                    if titulo_elem:
                        titulo = titulo_elem.get_text(strip=True)
                    else:
                        # Pegar do atributo title ou alt
                        titulo = link_elem.get('title') or link_elem.get('alt')
                    
                    if not titulo:
                        titulo = link_elem.get_text(strip=True)[:100]
                    
                    # Extrair preço
                    preco_elem = item.find('span', {'class': lambda x: x and 'price' in x}) or \
                                 item.find('div', {'class': lambda x: x and 'price' in x}) or \
                                 item.find('strong')
                    preco = preco_elem.get_text(strip=True) if preco_elem else 'Sob consulta'
                    
                    # Extrair URL
                    url_anuncio = link_elem.get('href', '#')
                    
                    # Garantir que a URL é absoluta
                    if url_anuncio.startswith('/'):
                        url_anuncio = f"https://www.olx.pt{url_anuncio}"
                    elif not url_anuncio.startswith('http'):
                        url_anuncio = urljoin('https://www.olx.pt', url_anuncio)
                    
                    # Validar dados
                    if titulo and len(titulo) > 5 and url_anuncio.startswith('http'):
                        anuncios.append({
                            'titulo': titulo,
                            'preco': preco,
                            'url': url_anuncio
                        })
                        logger.info(f"✓ Adicionado: {titulo[:50]}... | {preco}")
                        
                        # ⏸️ DELAY entre itens: aguardar um pouco entre cada item para não parecer bot
                        time.sleep(random.uniform(0.5, 1.5))
                except Exception as e:
                    logger.debug(f"Erro ao processar item OLX: {e}")
                    continue
            
            print(f"✅ {len(anuncios)} anúncios encontrados no OLX")
            
            return {
                'plataforma': 'OLX Portugal',
                'total_anuncios': len(anuncios),
                'anuncios': anuncios,
                'url_busca': url,
                'data_busca': self.timestamp
            }
        except Exception as e:
            print(f"❌ Erro ao buscar OLX: {e}")
            logger.exception("Stack trace:")
            return None
    
    def monitorar_veiculo(self, modelo, nome_arquivo):
        """
        Monitora um veículo em ambas as plataformas
        """
        print(f"\n{'='*60}")
        print(f"📋 Monitorando: {modelo}")
        print(f"{'='*60}")
        
        dados = {
            'veiculo': modelo,
            'data_atualizacao': self.timestamp,
            'plataformas': []
        }
        
        # Buscar em ambas plataformas
        sv = self.buscar_standvirtual(modelo)
        if sv:
            dados['plataformas'].append(sv)
        
        # Delay entre plataformas
        time.sleep(random.uniform(3, 6))
        
        olx = self.buscar_olx(modelo)
        if olx:
            dados['plataformas'].append(olx)
        
        # Salvar dados atuais
        arquivo_atual = DADOS_DIR / nome_arquivo
        with open(arquivo_atual, 'w', encoding='utf-8') as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
        print(f"✅ Dados salvos em: {arquivo_atual}")
        
        # Salvar no histórico
        data_hoje = datetime.now().strftime('%Y-%m-%d')
        hora_atual = datetime.now().strftime('%H%M%S')
        arquivo_historico = HISTORICO_DIR / f"{data_hoje}-{hora_atual}.json"
        with open(arquivo_historico, 'w', encoding='utf-8') as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
        print(f"📁 Histórico salvo em: {arquivo_historico}")
        
        return dados
    
    def executar(self):
        """
        Executa o monitoramento completo
        """
        print(f"\n🚀 Monitor Automóvel iniciado em {self.timestamp}")
        print(f"📋 Plataformas: Standvirtual, OLX Portugal")
        print(f"🏍️ Veículos: Yamaha NMAX, BMW Série 3")
        
        # Monitorar Yamaha NMAX
        self.monitorar_veiculo('Yamaha NMAX', 'yamaha-nmax.json')
        
        # Delay maior entre veículos
        time.sleep(random.uniform(6, 10))
        
        # Monitorar BMW Série 3
        self.monitorar_veiculo('BMW Série 3', 'bmw-serie3.json')
        
        print(f"\n✨ Monitoramento concluído com sucesso!")
        print(f"📁 Dados salvos em: {DADOS_DIR}")
        print(f"⏰ Próxima busca: confira o GitHub Actions para detalhes")

if __name__ == '__main__':
    monitor = MonitorAutomovel()
    monitor.executar()
