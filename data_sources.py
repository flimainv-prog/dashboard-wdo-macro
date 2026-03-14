# data_sources.py
import yfinance as yf
import pandas as pd
import numpy as np
import streamlit as st
from datetime import datetime, timedelta
import pytz
import time

BRT = pytz.timezone('America/Sao_Paulo')
CACHE_TTL_SECONDS = 300

# TICKERS REAIS
ATIVOS_VERDE = [
    'DX-Y.NYB', '^VIX', 'GC=F', '^TNX', 'USDMXN=X', 'USDZAR=X', 'CL=F'
]

ATIVOS_VERMELHA = [
    '^GSPC', 'QQQ', 'EWZ', '^BVSP', 'EURUSD=X', 'GBPUSD=X', 'BTC-USD'
]

def fetch_com_retry(ticker, period='5d', interval='5m', tentativas=2):
    """Tenta buscar dados com retry automático"""
    for i in range(tentativas):
        try:
            df = yf.download(ticker, period=period, interval=interval, 
                            progress=False, auto_adjust=True, prepost=True)
            if not df.empty:
                return df
        except Exception as e:
            if i < tentativas - 1:
                time.sleep(1)
            continue
    return pd.DataFrame()

@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_vix():
    try:
        vix = yf.download('^VIX', period='2d', interval='1h', 
                         progress=False, auto_adjust=True)
        if vix.empty:
            return None
        if isinstance(vix.columns, pd.MultiIndex):
            vix.columns = vix.columns.get_level_values(0)
        return float(vix['Close'].dropna().iloc[-1])
    except:
        return None

@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_wdo_dates():
    """Retorna últimas 30 datas úteis"""
    try:
        raw = yf.download('BRL=X', period='60d', interval='1d', progress=False)
        if raw.empty:
            end_date = datetime.now(BRT).date()
            return [(end_date - timedelta(days=i)) for i in range(1, 31)]
        dates = [d.date() for d in raw.index if d.date().weekday() < 5]
        return sorted(dates, reverse=True)[:30]
    except:
        end_date = datetime.now(BRT).date()
        return [(end_date - timedelta(days=i)) for i in range(1, 31)]

@st.cache_data(ttl=CACHE_TTL_SECONDS)
def fetch_todos(tickers_list, target_date_str, candle_ref):
    """Baixa dados para um dia específico"""
    target = pd.Timestamp(target_date_str).date()
    
    try:
        raw = yf.download(
            tickers_list, period="60d", interval="5m",
            progress=False, prepost=True, auto_adjust=True, 
            group_by='ticker', threads=False
        )
        
        if raw.empty:
            return pd.DataFrame()
        
        if not isinstance(raw.columns, pd.MultiIndex):
            return pd.DataFrame()
        
        raw.index = raw.index.tz_convert(BRT) if raw.index.tz is None else raw.index.tz_convert(BRT)
        
        result = {}
        for ticker in tickers_list:
            try:
                s = raw[ticker]['Close']
                s_filtrada = s[s.index.date == target]
                if not s_filtrada.empty:
                    result[ticker] = s_filtrada.fillna(method='ffill')
            except:
                continue
        
        return pd.DataFrame(result) if result else pd.DataFrame()
    
    except Exception as e:
        return pd.DataFrame()

@st.cache_data(ttl=CACHE_TTL_SECONDS)
def contar_ativos(tickers_list, target_date_str, candle_ref, threshold=3):
    """Conta ativos em alta vs. abertura"""
    df = fetch_todos(tickers_list, target_date_str, candle_ref)
    
    if df.empty:
        return pd.Series(dtype=float)
    
    series_list = []
    for ticker in df.columns:
        try:
            s = df[ticker].dropna()
            if s.empty or len(s) < 2:
                continue
            
            abertura = float(s.values[0])
            if abertura == 0:
                continue
            
            pct = 100 * (df[ticker] - abertura) / abs(abertura)
            series_list.append(pct)
        except:
            continue
    
    if not series_list:
        return pd.Series(dtype=float)
    
    return (pd.concat(series_list, axis=1) > threshold).sum(axis=1).astype(float)

@st.cache_data(ttl=CACHE_TTL_SECONDS)
def fetch_linha_azul_v2(target_date_str, candle_ref):
    """Calcula Linha Azul v2 simplificada"""
    target = pd.Timestamp(target_date_str).date()
    
    try:
        tickers = ['USDMXN=X', 'DX-Y.NYB', '^VIX', '^TNX']
        df = fetch_todos(tickers, target_date_str, candle_ref)
        
        if df.empty:
            return pd.Series(dtype=float)
        
        scores = []
        for col in df.columns:
            try:
                s = df[col].dropna()
                if len(s) < 2:
                    continue
                
                media = s.rolling(window=10, min_periods=1).mean()
                std = s.rolling(window=10, min_periods=1).std().replace(0, 1)
                z_score = (s - media) / std
                scores.append(z_score)
            except:
                continue
        
        if not scores:
            return pd.Series(dtype=float)
        
        linha_azul = pd.concat(scores, axis=1).mean(axis=1)
        ema = linha_azul.ewm(span=10, adjust=False).mean()
        
        return ema.round(2)
    
    except Exception as e:
        return pd.Series(dtype=float)

def fetch_roro_score(verde_count, vermelha_count):
    """RoRo simples"""
    try:
        if verde_count.empty or vermelha_count.empty:
            return pd.Series(dtype=float)
        
        den = (verde_count + vermelha_count).replace(0, np.nan)
        score_roro = (100 * (verde_count - vermelha_count) / den).fillna(0)
        
        return score_roro
    except:
        return pd.Series(dtype=float)

def ultimo_candle_real():
    """Retorna timestamp do último candle real"""
    agora = datetime.now(BRT)
    m = agora.replace(second=0, microsecond=0)
    m = m - timedelta(minutes=m.minute % 5)
    return pd.Timestamp(m)
