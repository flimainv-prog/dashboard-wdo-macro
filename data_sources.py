import pandas as pd
import numpy as np
import yfinance as yf
import pytz
import streamlit as st
from datetime import datetime, timedelta
import time

# Constantes para tickers
WDO_TICKER = 'WDO=F'
BRL_TICKER = 'BRL=X'
VERDE_TICKER = '^BVSP'  # IBOV para Verde
VERMELHA_TICKER = '^GSPC'  # S&P 500 para Vermelha

# Função auxiliar para buscar dados com retry
def fetch_yf_data(ticker, start=None, end=None, period='1y', interval='1d', retries=3):
    for attempt in range(retries):
        try:
            data = yf.download(ticker, start=start, end=end, period=period, interval=interval)
            return data
        except Exception as e:
            if attempt == retries - 1:
                st.error(f"Falha ao buscar {ticker} após {retries} tentativas: {e}")
                return pd.DataFrame()
            time.sleep(1)
    return pd.DataFrame()

@st.cache_data
def get_vix():
    return fetch_yf_data('^VIX')

@st.cache_data
def get_wdo_dates():
    data = fetch_yf_data(WDO_TICKER)
    return data.index

@st.cache_data
def contar_ativos():
    tickers = [WDO_TICKER, BRL_TICKER, VERDE_TICKER, VERMELHA_TICKER]
    count = 0
    for ticker in tickers:
        data = fetch_yf_data(ticker, period='1d')
        if not data.empty:
            count += 1
    return count

@st.cache_data
def fetch_linha_azul_v2():
    data = fetch_yf_data(WDO_TICKER)
    if not data.empty:
        data['Linha_Azul'] = data['Close'].rolling(window=20).mean()  # SMA de 20 dias como exemplo
    return data

@st.cache_data
def fetch_roro_score():
    data = fetch_yf_data(WDO_TICKER)
    if not data.empty:
        data['Roro_Score'] = ((data['Close'] - data['Open']) / data['Open']) * 100  # Score exemplo baseado em variação percentual
    return data

@st.cache_data
def fetch_todos():
    tickers = [WDO_TICKER, BRL_TICKER, VERDE_TICKER, VERMELHA_TICKER, '^VIX']
    data = {}
    for ticker in tickers:
        data[ticker] = fetch_yf_data(ticker)
    return data

@st.cache_data
def último_candle_real():
    data = fetch_yf_data(WDO_TICKER, period='1d', interval='1m')
    if not data.empty:
        # Filtrar para dias úteis (segunda a sexta), mas como é intraday, pegar o último disponível
        # Para flexibilidade, não forçar horário específico
        return data.iloc[-1]
    return None
