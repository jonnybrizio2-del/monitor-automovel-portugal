#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Monitor de Mercado Automóvel - Portugal
Rastreamento de preços para Yamaha NMAX, BMW Série 3, Toyota Corolla e Astra 2015
Plataformas: Standvirtual, OLX Portugal, Facebook Marketplace, Auto.pt e CustoJusto
"""

import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime
from pathlib import Path
import time
import random
from urllib.parse import urljoin, quote
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
    'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1'
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
    
    def _get_with_retry(self, url, timeout=15, site_name='Standvirtual'):
        """
        Faz requisição com retry automático e delays maiores conforme o site
        """
        for attempt in range(self.max_retries):
            try:
                # Atualizar User-Agent a cada tentativa
                self.session.headers['User-Agent'] = random.choice(USER_AGENTS)
                
                logger.info(f"Tentativa {attempt + 1}/{self.max_retries} para {site_name}: {url}")
                response = self.session.get(url, timeout=timeout, allow_redirects=True)
                response.raise_for_status()
                return response
            except requests.exceptions.RequestException as e:
                logger.warning(f"Erro na tentativa {attempt + 1}: {e}")
                if attempt < self.max_retries - 1:
                    # Delay diferente conforme o site
                    if site_name in ['Facebook Marketplace']:
                        wait_time = (self.retry_delay * (attempt + 3)) + random.uniform(5, 12)
                    elif site_name in ['OLX', 'CustoJusto']:
                        wait_time = (self.retry_delay * (attempt + 2)) + random.uniform(3, 8)
                    else:
                        wait_time = self.retry_delay * (attempt + 1) + random.uniform(0, 2)
                    logger.info(f"Aguardando {wait_time:.1f}s antes de tentar novamente...")
                    time.sleep(wait_time)
                else:
                    raise
    
    def buscar_standvirtual(self, modelo):
        """
        Busca anúncios no Standvirtual
        """
        print(f"\n🔍 Buscando '{modelo}' no Standvirtual...")
        try:
            urls_sv = {
                'Yamaha NMAX': 'https://www.standvirtual.com/anuncios/motos-scooters-ciclomotores?searchText=Yamaha+NMAX&sort_by=created_at_desc',
                'BMW Série 3': 'https://www.standvirtual.com/anuncios/automoveis?searchText=BMW+Serie+3&sort_by=created_at_desc',
                'Toyota Corolla': 'https://www.standvirtual.com/anuncios/automoveis?searchText=Toyota+Corolla&sort_by=created_at_desc',
                'Astra 2015': 'https://www.standvirtual.com/anuncios/automoveis?searchText=Opel+Astra+2015&sort_by=created_at_desc'
            }
            
            url = urls_sv.get(modelo)
            if not url:
                print(f"⚠️ Modelo não configurado: {modelo}")
                return None
            
            response = self._get_with_retry(url, site_name='Standvirtual')
            soup = BeautifulSoup(response.content, 'html.parser')
            
            anuncios = []
            items = soup.find_all('article', {'class': lambda x: x and 'item' in x})
            
            if not items:
                items = soup.find_all('div', {'data-testid': 'listing-item'})
            
            if not items:
                items = soup.find_all('a', {'class': lambda x: x and 'link' in x})
            
            logger.info(f"Encontrados {len(items)} itens no Standvirtual")
            
            for item in items[:30]:
                try:
                    link_elem = item.find('a', href=True)
                    if not link_elem:
                        link_elem = item if item.name == 'a' else None
                    
                    if not link_elem:
                        continue
                    
                    titulo_elem = item.find('h2') or item.find('h3') or item.find('span', {'class': lambda x: x and 'title' in x})
                    titulo = titulo_elem.get_text(strip=True) if titulo_elem else None
                    
                    if not titulo:
                        titulo = link_elem.get_text(strip=True)[:100]
                    
                    preco_elem = item.find('span', {'class': lambda x: x and 'price' in x}) or \
                                 item.find('p', {'class': lambda x: x and 'price' in x}) or \
                                 item.find('strong')
                    preco = preco_elem.get_text(strip=True) if preco_elem else 'Sob consulta'
                    
                    url_anuncio = link_elem.get('href', '#')
                    
                    if url_anuncio.startswith('/'):
                        url_anuncio = f"https://www.standvirtual.com{url_anuncio}"
                    elif not url_anuncio.startswith('http'):
                        url_anuncio = urljoin('https://www.standvirtual.com', url_anuncio)
                    
                    if titulo and len(titulo) > 5 and url_anuncio.startswith('http'):
                        anuncios.append({
                            'titulo': titulo,
                            'preco': preco,
                            'url': url_anuncio
                        })
                        logger.info(f"✓ Standvirtual: {titulo[:50]}...")
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
        Busca anúncios no OLX Portugal
        """
        print(f"🔍 Buscando '{modelo}' no OLX...")
        try:
            urls_olx = {
                'Yamaha NMAX': 'https://www.olx.pt/search/q-yamaha-nmax/',
                'BMW Série 3': 'https://www.olx.pt/search/q-bmw-serie-3/',
                'Toyota Corolla': 'https://www.olx.pt/search/q-toyota-corolla/',
                'Astra 2015': 'https://www.olx.pt/search/q-astra-2015/'
            }
            
            url = urls_olx.get(modelo)
            if not url:
                print(f"⚠️ Modelo não configurado: {modelo}")
                return None
            
            delay = random.uniform(8, 15)
            logger.info(f"⏸️  Aguardando {delay:.1f}s antes de acessar OLX...")
            print(f"⏸️  Aguardando {delay:.1f}s antes de acessar OLX...")
            time.sleep(delay)
            
            headers_olx = self.headers.copy()
            headers_olx['Referer'] = 'https://www.olx.pt/'
            headers_olx['Origin'] = 'https://www.olx.pt'
            headers_olx['Pragma'] = 'no-cache'
            self.session.headers.update(headers_olx)
            
            response = self._get_with_retry(url, timeout=20, site_name='OLX')
            soup = BeautifulSoup(response.content, 'html.parser')
            
            anuncios = []
            items = soup.find_all('div', {'data-cy': 'listing-item'})
            
            if not items:
                items = soup.find_all('a', {'class': lambda x: x and 'listing' in x})
            
            if not items:
                items = soup.find_all('a', {'href': lambda x: x and '/anuncio/' in x})
            
            logger.info(f"Encontrados {len(items)} itens no OLX")
            
            for item in items[:30]:
                try:
                    link_elem = item.find('a', href=True) if item.name != 'a' else item
                    
                    if not link_elem:
                        continue
                    
                    titulo = link_elem.get_text(strip=True)[:100]
                    preco = 'Sob consulta'
                    url_anuncio = link_elem.get('href', '#')
                    
                    if url_anuncio.startswith('/'):
                        url_anuncio = f"https://www.olx.pt{url_anuncio}"
                    elif not url_anuncio.startswith('http'):
                        url_anuncio = urljoin('https://www.olx.pt', url_anuncio)
                    
                    if titulo and len(titulo) > 5 and url_anuncio.startswith('http'):
                        anuncios.append({
                            'titulo': titulo,
                            'preco': preco,
                            'url': url_anuncio
                        })
                        logger.info(f"✓ OLX: {titulo[:50]}...")
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
    
    def buscar_auto_pt(self, modelo):
        """
        Busca anúncios no Auto.pt
        """
        print(f"🔍 Buscando '{modelo}' no Auto.pt...")
        try:
            # Auto.pt - API similar ao OLX
            modelo_search = modelo.lower().replace(' ', '-')
            
            urls_auto = {
                'Yamaha NMAX': 'https://www.auto.pt/pesquisa/Mota/Yamaha/NMAX',
                'BMW Série 3': 'https://www.auto.pt/pesquisa/Automovel/BMW/Serie-3',
                'Toyota Corolla': 'https://www.auto.pt/pesquisa/Automovel/Toyota/Corolla',
                'Astra 2015': 'https://www.auto.pt/pesquisa/Automovel/Opel/Astra'
            }
            
            url = urls_auto.get(modelo)
            if not url:
                print(f"⚠️ Modelo não configurado no Auto.pt: {modelo}")
                return None
            
            delay = random.uniform(6, 12)
            logger.info(f"⏸️  Aguardando {delay:.1f}s antes de acessar Auto.pt...")
            print(f"⏸️  Aguardando {delay:.1f}s antes de acessar Auto.pt...")
            time.sleep(delay)
            
            headers_auto = self.headers.copy()
            headers_auto['Referer'] = 'https://www.auto.pt/'
            headers_auto['Origin'] = 'https://www.auto.pt'
            self.session.headers.update(headers_auto)
            
            response = self._get_with_retry(url, timeout=20, site_name='Auto.pt')
            soup = BeautifulSoup(response.content, 'html.parser')
            
            anuncios = []
            items = soup.find_all('div', {'class': lambda x: x and 'anuncio' in x.lower()})
            
            if not items:
                items = soup.find_all('article')
            
            if not items:
                items = soup.find_all('a', {'href': lambda x: x and '/veiculo/' in x})
            
            logger.info(f"Encontrados {len(items)} itens no Auto.pt")
            
            for item in items[:30]:
                try:
                    link_elem = item.find('a', href=True) if item.name != 'a' else item
                    
                    if not link_elem:
                        continue
                    
                    titulo = link_elem.get_text(strip=True)[:100]
                    
                    preco_elem = item.find('span', {'class': lambda x: x and 'preco' in x.lower()})
                    preco = preco_elem.get_text(strip=True) if preco_elem else 'Sob consulta'
                    
                    url_anuncio = link_elem.get('href', '#')
                    
                    if url_anuncio.startswith('/'):
                        url_anuncio = f"https://www.auto.pt{url_anuncio}"
                    elif not url_anuncio.startswith('http'):
                        url_anuncio = urljoin('https://www.auto.pt', url_anuncio)
                    
                    if titulo and len(titulo) > 5 and url_anuncio.startswith('http'):
                        anuncios.append({
                            'titulo': titulo,
                            'preco': preco,
                            'url': url_anuncio
                        })
                        logger.info(f"✓ Auto.pt: {titulo[:50]}...")
                        time.sleep(random.uniform(0.5, 1.2))
                except Exception as e:
                    logger.debug(f"Erro ao processar item Auto.pt: {e}")
                    continue
            
            print(f"✅ {len(anuncios)} anúncios encontrados no Auto.pt")
            
            return {
                'plataforma': 'Auto.pt',
                'total_anuncios': len(anuncios),
                'anuncios': anuncios,
                'url_busca': url,
                'data_busca': self.timestamp
            }
        except Exception as e:
            print(f"❌ Erro ao buscar Auto.pt: {e}")
            logger.exception("Stack trace:")
            return None
    
    def buscar_custojusto(self, modelo):
        """
        Busca anúncios no CustoJusto
        """
        print(f"🔍 Buscando '{modelo}' no CustoJusto...")
        try:
            urls_cj = {
                'Yamaha NMAX': 'https://www.custojusto.pt/search?q=yamaha+nmax',
                'BMW Série 3': 'https://www.custojusto.pt/search?q=bmw+serie+3',
                'Toyota Corolla': 'https://www.custojusto.pt/search?q=toyota+corolla',
                'Astra 2015': 'https://www.custojusto.pt/search?q=astra+2015'
            }
            
            url = urls_cj.get(modelo)
            if not url:
                print(f"⚠️ Modelo não configurado no CustoJusto: {modelo}")
                return None
            
            delay = random.uniform(7, 14)
            logger.info(f"⏸️  Aguardando {delay:.1f}s antes de acessar CustoJusto...")
            print(f"⏸️  Aguardando {delay:.1f}s antes de acessar CustoJusto...")
            time.sleep(delay)
            
            headers_cj = self.headers.copy()
            headers_cj['Referer'] = 'https://www.custojusto.pt/'
            headers_cj['Origin'] = 'https://www.custojusto.pt'
            self.session.headers.update(headers_cj)
            
            response = self._get_with_retry(url, timeout=20, site_name='CustoJusto')
            soup = BeautifulSoup(response.content, 'html.parser')
            
            anuncios = []
            items = soup.find_all('div', {'class': lambda x: x and 'listing' in x.lower()})
            
            if not items:
                items = soup.find_all('article')
            
            if not items:
                items = soup.find_all('a', {'href': lambda x: x and '/ads/' in x})
            
            logger.info(f"Encontrados {len(items)} itens no CustoJusto")
            
            for item in items[:30]:
                try:
                    link_elem = item.find('a', href=True) if item.name != 'a' else item
                    
                    if not link_elem:
                        continue
                    
                    titulo = link_elem.get_text(strip=True)[:100]
                    
                    preco_elem = item.find('span', {'class': lambda x: x and 'price' in x.lower()})
                    preco = preco_elem.get_text(strip=True) if preco_elem else 'Sob consulta'
                    
                    url_anuncio = link_elem.get('href', '#')
                    
                    if url_anuncio.startswith('/'):
                        url_anuncio = f"https://www.custojusto.pt{url_anuncio}"
                    elif not url_anuncio.startswith('http'):
                        url_anuncio = urljoin('https://www.custojusto.pt', url_anuncio)
                    
                    if titulo and len(titulo) > 5 and url_anuncio.startswith('http'):
                        anuncios.append({
                            'titulo': titulo,
                            'preco': preco,
                            'url': url_anuncio
                        })
                        logger.info(f"✓ CustoJusto: {titulo[:50]}...")
                        time.sleep(random.uniform(0.5, 1.2))
                except Exception as e:
                    logger.debug(f"Erro ao processar item CustoJusto: {e}")
                    continue
            
            print(f"✅ {len(anuncios)} anúncios encontrados no CustoJusto")
            
            return {
                'plataforma': 'CustoJusto',
                'total_anuncios': len(anuncios),
                'anuncios': anuncios,
                'url_busca': url,
                'data_busca': self.timestamp
            }
        except Exception as e:
            print(f"❌ Erro ao buscar CustoJusto: {e}")
            logger.exception("Stack trace:")
            return None
    
    def buscar_facebook_marketplace(self, modelo):
        """
        Busca anúncios no Facebook Marketplace Portugal
        """
        print(f"🔍 Buscando '{modelo}' no Facebook Marketplace...")
        try:
            query = quote(modelo)
            url = f'https://www.facebook.com/marketplace/pt-PT/search?query={query}&sortBy=creation_time_descending'
            
            delay = random.uniform(10, 20)
            logger.info(f"⏸️  Aguardando {delay:.1f}s antes de acessar Facebook...")
            print(f"⏸️  Aguardando {delay:.1f}s antes de acessar Facebook...")
            time.sleep(delay)
            
            headers_fb = self.headers.copy()
            headers_fb['Referer'] = 'https://www.facebook.com/'
            headers_fb['Origin'] = 'https://www.facebook.com'
            self.session.headers.update(headers_fb)
            
            response = self._get_with_retry(url, timeout=20, site_name='Facebook Marketplace')
            soup = BeautifulSoup(response.content, 'html.parser')
            
            anuncios = []
            items = soup.find_all('div', {'class': lambda x: x and 'listing' in x.lower()})
            
            if not items:
                items = soup.find_all('a', {'href': lambda x: x and '/marketplace/' in x})
            
            logger.info(f"Encontrados {len(items)} itens no Facebook Marketplace")
            
            if len(items) == 0:
                logger.warning("⚠️ Facebook Marketplace requer JavaScript para carregar conteúdo")
                print(f"⚠️ Facebook Marketplace pode não retornar resultados (requer JavaScript)")
                return {
                    'plataforma': 'Facebook Marketplace',
                    'total_anuncios': 0,
                    'anuncios': [],
                    'url_busca': url,
                    'data_busca': self.timestamp,
                    'nota': 'Requer JavaScript'
                }
            
            for item in items[:30]:
                try:
                    link_elem = item.find('a', href=True) if item.name != 'a' else item
                    
                    if not link_elem:
                        continue
                    
                    titulo = link_elem.get_text(strip=True)[:100]
                    preco = 'Sob consulta'
                    url_anuncio = link_elem.get('href', '#')
                    
                    if not url_anuncio.startswith('http'):
                        url_anuncio = f"https://www.facebook.com{url_anuncio}"
                    
                    if titulo and len(titulo) > 5 and url_anuncio.startswith('http'):
                        anuncios.append({
                            'titulo': titulo,
                            'preco': preco,
                            'url': url_anuncio
                        })
                        logger.info(f"✓ Facebook: {titulo[:50]}...")
                        time.sleep(random.uniform(1, 2))
                except Exception as e:
                    logger.debug(f"Erro ao processar item Facebook: {e}")
                    continue
            
            print(f"✅ {len(anuncios)} anúncios encontrados no Facebook Marketplace")
            
            return {
                'plataforma': 'Facebook Marketplace',
                'total_anuncios': len(anuncios),
                'anuncios': anuncios,
                'url_busca': url,
                'data_busca': self.timestamp
            }
        except Exception as e:
            print(f"❌ Erro ao buscar Facebook Marketplace: {e}")
            logger.exception("Stack trace:")
            return None
    
    def monitorar_veiculo(self, modelo, nome_arquivo):
        """
        Monitora um veículo em todas as 5 plataformas
        """
        print(f"\n{'='*60}")
        print(f"📋 Monitorando: {modelo}")
        print(f"{'='*60}")
        
        dados = {
            'veiculo': modelo,
            'data_atualizacao': self.timestamp,
            'plataformas': []
        }
        
        # Plataformas a buscar
        plataformas = [
            ('standvirtual', self.buscar_standvirtual),
            ('auto.pt', self.buscar_auto_pt),
            ('olx', self.buscar_olx),
            ('custojusto', self.buscar_custojusto),
            ('facebook', self.buscar_facebook_marketplace)
        ]
        
        for nome_plat, funcao_busca in plataformas:
            resultado = funcao_busca(modelo)
            if resultado:
                dados['plataformas'].append(resultado)
            
            # Delay entre plataformas
            time.sleep(random.uniform(3, 6))
        
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
        Executa o monitoramento completo de todos os 4 veículos em 5 plataformas
        """
        print(f"\n🚀 Monitor Automóvel iniciado em {self.timestamp}")
        print(f"📋 Plataformas: Standvirtual, Auto.pt, OLX, CustoJusto, Facebook Marketplace")
        print(f"🚗 Veículos: Yamaha NMAX, BMW Série 3, Toyota Corolla, Astra 2015")
        
        veiculos = [
            ('Yamaha NMAX', 'yamaha-nmax.json'),
            ('BMW Série 3', 'bmw-serie3.json'),
            ('Toyota Corolla', 'toyota-corolla.json'),
            ('Astra 2015', 'astra-2015.json')
        ]
        
        for i, (modelo, arquivo) in enumerate(veiculos):
            self.monitorar_veiculo(modelo, arquivo)
            
            # Delay entre veículos
            if i < len(veiculos) - 1:
                delay = random.uniform(10, 20)
                logger.info(f"Aguardando {delay:.1f}s antes do próximo veículo...")
                print(f"⏸️  Aguardando {delay:.1f}s antes do próximo veículo...")
                time.sleep(delay)
        
        print(f"\n✨ Monitoramento concluído com sucesso!")
        print(f"📁 Dados salvos em: {DADOS_DIR}")
        print(f"📊 Resumo: 4 veículos × 5 plataformas = 20 buscas no total")

if __name__ == '__main__':
    monitor = MonitorAutomovel()
    monitor.executar()
