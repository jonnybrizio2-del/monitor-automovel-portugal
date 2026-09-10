# 📊 Monitor de Mercado Automóvel - Portugal

Sistema de monitoramento de preços e anúncios para veículos em Portugal.

## 🏍️ Veículos Monitorados

- **Yamaha NMAX** - Ciclomotor desportivo
- **BMW Série 3** - Automóvel de médio segmento

## 📍 Plataformas

- [Standvirtual](https://standvirtual.com)
- [OLX Portugal](https://olx.pt)

## 📁 Estrutura de Dados

Os resultados são armazenados em JSON com links dos anúncios:

```
dados/
├── yamaha-nmax.json
├── bmw-serie3.json
└── historico/
    └── YYYY-MM-DD.json
```

## 📊 Formato dos Dados

Cada arquivo JSON contém:
- Informações do veículo
- Total de anúncios por plataforma
- Preços (mínimo, máximo, média)
- **Links diretos para cada anúncio**
- Data da última atualização

## 🔄 Atualização

Os dados são atualizados regularmente e versionados no Git para rastreamento histórico.
