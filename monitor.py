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

# Criar diretório de dados se não existir
DADOS_DIR = Path('dados')
DADOS_DIR.mkdir(exist_ok=True)
HISTORICO_DIR = DADOS_DIR / 'historico'
HISTORICO_DIR.mkdir(exist_ok=True)

class MonitorAutomovel:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.timestamp = datetime.now().isoformat()
    
    def buscar_standvirtual(self, modelo):
        """
        Busca anúncios no Standvirtual
        """
        print(f"\n🔍 Buscando '{modelo}' no Standvirtual...")
        try:
            # URLs para busca no Standvirtual
            urls_sv = {
                'Yamaha NMAX': 'https://www.standvirtual.com/anuncios/motos-scooters-ciclomotores?searchText=Yamaha+NMAX',
                'BMW Série 3': 'https://www.standvirtual.com/anuncios/automoveis?searchText=BMW+Serie+3'
            }
            
            url = urls_sv.get(modelo)
            if not url:
                print(f"⚠️ Modelo não configurado: {modelo}")
                return None
            
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extrair dados do Standvirtual
            anuncios = []
            
            # Procurar por elementos de anúncio
            items = soup.find_all('article', {'class': 'item'})
            
            for item in items[:20]:  # Limitar a 20 resultados
                try:
                    titulo = item.find('h2')
                    preco = item.find('p', {'class': 'price'})
                    link = item.find('a', {'class': 'item-link'})
                    
                    if titulo and link:
                        anuncios.append({
                            'titulo': titulo.get_text(strip=True),
                            'preco': preco.get_text(strip=True) if preco else 'N/A',
                            'url': link.get('href', '#')
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
            
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extrair dados do OLX
            anuncios = []
            
            # Procurar por elementos de anúncio
            items = soup.find_all('div', {'class': 'OLXad-list-item'})
            
            for item in items[:20]:  # Limitar a 20 resultados
                try:
                    titulo = item.find('h2')
                    preco = item.find('span', {'class': 'price'})
                    link = item.find('a')
                    
                    if titulo and link:
                        anuncios.append({
                            'titulo': titulo.get_text(strip=True),
                            'preco': preco.get_text(strip=True) if preco else 'N/A',
                            'url': link.get('href', '#')
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
