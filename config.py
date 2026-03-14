# config.py
import pytz
from datetime import datetime, timedelta

# ============================================================================
# TIMEZONE E CALENDÁRIO
# ============================================================================

BRT = pytz.timezone('America/Sao_Paulo')

AUTO_REFRESH_INTERVAL_MS = 300000  # 5 minutos
CACHE_TTL_SECONDS = 300  # 5 minutos

FERIADOS_BR_2026 = [
    "2026-01-01", "2026-02-16", "2026-02-17", "2026-04-03",
    "2026-04-21", "2026-05-01", "2026-06-04", "2026-09-07",
    "2026-10-12", "2026-11-02", "2026-11-15", "2026-11-20",
    "2026-12-25"
]

def get_feriados_br():
    """Retorna lista de feriados brasileiros"""
    return FERIADOS_BR_2026

# ============================================================================
# ATIVOS - VERDE (Dólar Comprador)
# ============================================================================

ATIVOS_VERDE = [
    'DX-Y.NYB',      # DXY - Índice do Dólar
    '^VIX',          # VIX - Volatilidade
    'GC=F',          # Ouro
    'SI=F',          # Prata
    '^TNX',          # Treasury 10Y
    '^FVX',          # Treasury 5Y
    '^IRX',          # Treasury 3M
    'ZB=F',          # Bond Futuro
    'USDCAD=X',      # USD/CAD
    'USDJPY=X',      # USD/JPY
    'USDCHF=X',      # USD/CHF
    'USDSEK=X',      # USD/SEK
    'USDMXN=X',      # USD/MXN (IMPORTANTE!)
    'USDZAR=X',      # USD/ZAR
    'USDTRY=X',      # USD/TRY
    'CL=F',          # Petróleo
    'NG=F'           # Gás Natural
]

# ============================================================================
# ATIVOS - VERMELHA (Dólar Vendedor)
# ============================================================================

ATIVOS_VERMELHA = [
    'SPY',           # S&P 500
    'QQQ',           # NASDAQ
    'EWZ',           # Brasil (ETF)
    'EEM',           # Emergentes
    'GLD',           # Ouro (ETF)
    'TLT',           # Bonds (ETF)
    'EURUSD=X',      # EUR/USD
    'GBPUSD=X',      # GBP/USD
    'AUDUSD=X',      # AUD/USD
    'NZDUSD=X',      # NZD/USD
    '^GSPC',         # S&P 500 (índice)
    '^IXIC',         # NASDAQ (índice)
    '^BVSP',         # Bovespa
    '^HSI',          # Hang Seng
    '^N225',         # Nikkei
    '^FTSE',         # FTSE 100
    'HG=F',          # Cobre
    'BTC-USD'        # Bitcoin
]

# ============================================================================
# COMPONENTES DA LINHA AZUL v2
# ============================================================================

COMPONENTES_LINHA_AZUL = {
    'USDMXN=X': {
        'peso': 2.0,
        'descricao': 'Proxy de emergentes (pilar principal)',
        'transformacao': 'retorno_pct'
    },
    'DX-Y.NYB': {
        'peso': 1.5,
        'descricao': 'Força global do dólar',
        'transformacao': 'retorno_pct'
    },
    '^VIX': {
        'peso': 1.2,
        'descricao': 'Sentimento de medo/volatilidade',
        'transformacao': 'retorno_pct'
    },
    '^TNX': {
        'peso': 1.3,
        'descricao': 'Juros americanos 10Y',
        'transformacao': 'retorno_pct'
    },
    'USDZAR=X': {
        'peso': 0.9,
        'descricao': 'Emergentes auxiliar',
        'transformacao': 'retorno_pct'
    }
}

# ============================================================================
# PARÂMETROS TÉCNICOS
# ============================================================================

RSI_LENGTH = 14
EMA_SMOOTHING_LENGTH = 10
Z_SCORE_WINDOW = 20
THRESHOLD_ATIVOS = 0.03  # 3%

# Sinais
SPREAD_COMPRA = 3.0
SPREAD_VENDA = -3.0

# RoRo
RORO_COMPRA = 30.0
RORO_VENDA = -30.0

# VIX Regimes
VIX_CALMO = 15
VIX_NORMAL = 20
VIX_MODERADO = 25
VIX_ALTO = 30

# ============================================================================
# PREVISÃO DO PRÓXIMO CANDLE
# ============================================================================

PESOS_SCORE = {
    'rsi': 0.60,
    'momentum': 0.20,
    'tendencia': 0.15,
    'roro': 0.05
}

THRESHOLD_ALTA = 60
THRESHOLD_BAIXA = 40

# ============================================================================
# LOG E PERSISTÊNCIA
# ============================================================================

LOG_FILE = "wdo_macro_signals.csv"
MAX_LOG_ROWS = 10000

# ============================================================================
# LOGGING DO SISTEMA
# ============================================================================

import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)
