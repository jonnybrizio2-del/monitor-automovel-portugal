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
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15'
]

class MonitorAutomovel:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'pt-PT,pt;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Referer': 'https://www.google.com/',
        })
        self.timestamp = datetime.now().isoformat()
    
    def buscar_standvirtual(self, modelo):
        """
        Busca anúncios no Standvirtual
        """
        print(f"\n🔍 Buscando '{modelo}' no Standvirtual...")
        try:
            # URLs para busca no Standvirtual
            urls_sv = {
                'Yamaha NMAX': 'https://www.standvirtual.com/anuncios/motos-scooters-ciclomotores?searchText=Yamaha+NMAX&sort_by=created_at_desc',
                'BMW Série 3': 'https://www.standvirtual.com/anuncios/automoveis?searchText=BMW+Seria+3&sort_by=created_at_desc'
            }
            
            url = urls_sv.get(modelo)
            if not url:
                print(f"⚠️ Modelo não configurado: {modelo}")
                return None
            
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extrair dados do Standvirtual - atualizar seletores
            anuncios = []
            
            # Procurar por elementos de anúncio (múltiplos seletores possíveis)
            items = soup.find_all('div', {'class': 'ooa-1aoh7k3'})
            if not items:
                items = soup.find_all('article')
            if not items:
                items = soup.find_all('a', {'class': 'link-appearance'})
            
            for item in items[:20]:  # Limitar a 20 resultados
                try:
                    # Tentar diferentes formas de extrair dados
                    titulo_elem = item.find('h2') or item.find('span', {'class': 'title'})
                    preco_elem = item.find('p', {'class': 'price'}) or item.find('span', {'class': 'price'})
                    link_elem = item.find('a') or item
                    
                    titulo = titulo_elem.get_text(strip=True) if titulo_elem else 'N/A'
                    preco = preco_elem.get_text(strip=True) if preco_elem else 'N/A'
                    url_anuncio = link_elem.get('href', '#') if link_elem else '#'
                    
                    # Garantir que a URL é absoluta
                    if url_anuncio.startswith('/'):
                        url_anuncio = f"https://www.standvirtual.com{url_anuncio}"
                    
                    if titulo and titulo != 'N/A' and url_anuncio != '#':
                        anuncios.append({
                            'titulo': titulo,
                            'preco': preco,
                            'url': url_anuncio
                        })
                except Exception as e:
                    print(f"Erro ao processar item: {e}")
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
            return None
    
    def buscar_olx(self, modelo):
        """
        Busca anúncios no OLX Portugal
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
            
            # Adicionar delay para evitar bloqueio
            time.sleep(random.uniform(1, 3))
            
            response = self.session.get(url, timeout=15, allow_redirects=True)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extrair dados do OLX
            anuncios = []
            
            # Procurar por elementos de anúncio (múltiplos seletores possíveis)
            items = soup.find_all('div', {'class': 'OLXad-list-item'})
            if not items:
                items = soup.find_all('li', {'class': 'ad'})
            if not items:
                items = soup.find_all('div', {'class': 'listing-item'})
            
            for item in items[:20]:  # Limitar a 20 resultados
                try:
                    # Tentar diferentes formas de extrair dados
                    link_elem = item.find('a')
                    titulo = None
                    
                    # Tentar diferentes seletores para título
                    titulo_elem = item.find('h2') or item.find('span', {'class': 'title'})
                    if titulo_elem:
                        titulo = titulo_elem.get_text(strip=True)
                    elif link_elem and link_elem.get_text():
                        titulo = link_elem.get_text(strip=True)
                    
                    preco_elem = item.find('span', {'class': 'price'}) or item.find('p', {'class': 'price'})
                    preco = preco_elem.get_text(strip=True) if preco_elem else 'N/A'
                    
                    url_anuncio = link_elem.get('href', '#') if link_elem else '#'
                    
                    # Garantir que a URL é absoluta
                    if url_anuncio.startswith('/'):
                        url_anuncio = f"https://www.olx.pt{url_anuncio}"
                    
                    if titulo and url_anuncio != '#':
                        anuncios.append({
                            'titulo': titulo,
                            'preco': preco,
                            'url': url_anuncio
                        })
                except Exception as e:
                    print(f"Erro ao processar item: {e}")
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
        
        time.sleep(2)  # Aguardar entre requisições
        
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
        
        time.sleep(3)  # Aguardar entre veículos
        
        # Monitorar BMW Série 3
        self.monitorar_veiculo('BMW Série 3', 'bmw-serie3.json')
        
        print(f"\n✨ Monitoramento concluído com sucesso!")
        print(f"📁 Dados salvos em: {DADOS_DIR}")
        print(f"⏰ Próxima busca: confira o GitHub Actions para detalhes")

if __name__ == '__main__':
    monitor = MonitorAutomovel()
    monitor.executar()
