# data_sources.py
import yfinance as yf
import pandas as pd
import numpy as np
import streamlit as st
from datetime import datetime, timedelta
from config import (
    BRT, CACHE_TTL_SECONDS, ATIVOS_VERDE, ATIVOS_VERMELHA,
    COMPONENTES_LINHA_AZUL, THRESHOLD_ATIVOS, Z_SCORE_WINDOW,
    EMA_SMOOTHING_LENGTH, logger
)

# ============================================================================
# ÚLTIMO CANDLE REAL
# ============================================================================

def ultimo_candle_real():
    """Retorna o timestamp do último candle de 5 minutos completado"""
    agora = datetime.now(BRT)
    m = agora.replace(second=0, microsecond=0)
    m = m - timedelta(minutes=m.minute % 5)
    return pd.Timestamp(m)

# ============================================================================
# VIX ATUAL
# ============================================================================

@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_vix():
    """Busca VIX atual"""
    try:
        vix = yf.download('^VIX', period='2d', interval='1h', 
                         progress=False, auto_adjust=True)
        if vix.empty:
            return None
        
        if isinstance(vix.columns, pd.MultiIndex):
            vix.columns = vix.columns.get_level_values(0)
        
        return float(vix['Close'].dropna().iloc[-1])
    except Exception as e:
        logger.warning(f"Erro ao buscar VIX: {e}")
        return None

# ============================================================================
# DATAS DISPONÍVEIS
# ============================================================================

@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_wdo_dates():
    """Busca datas disponíveis do WDOFUT para seleção"""
    try:
        raw = yf.download('BRL=X', period='30d', interval='1d', 
                         progress=False)
        
        if raw.empty:
            end_date = datetime.now(BRT).date()
            return [(end_date - timedelta(days=i)) for i in range(7)]
        
        dates = [d.date() for d in raw.index if d.date().weekday() < 5]
        dates = sorted(dates, reverse=True)[:30]
        
        return dates if dates else [(datetime.now(BRT).date() - 
                                    timedelta(days=i)) for i in range(7)]
    except Exception as e:
        logger.warning(f"Erro ao buscar datas WDO: {e}")
        end_date = datetime.now(BRT).date()
        return [(end_date - timedelta(days=i)) for i in range(7)]

# ============================================================================
# DOWNLOAD DE TODOS OS ATIVOS
# ============================================================================

@st.cache_data(ttl=CACHE_TTL_SECONDS)
def fetch_todos(tickers_list, target_date_str, candle_ref):
    """Baixa dados de múltiplos tickers para um dia específico"""
    target = pd.Timestamp(target_date_str).date()
    
    try:
        raw = yf.download(
            tickers_list, period="7d", interval="5m",
            progress=False, prepost=True, auto_adjust=True, 
            group_by='ticker'
        )
        
        if raw.empty:
            return pd.DataFrame()
        
        if not isinstance(raw.columns, pd.MultiIndex):
            return pd.DataFrame()
        
        raw.index = raw.index.tz_convert(BRT)
        
        full_idx = pd.date_range(
            f"{target} 00:00", f"{target} 23:50", 
            freq='5T', tz=BRT
        )
        
        result = {}
        
        for ticker in tickers_list:
            try:
                s = raw[ticker]['Close']
                s = s[s.index.date == target]
                s = s.resample('5T').last().reindex(full_idx).ffill()
                result[ticker] = s
            except Exception:
                continue
        
        return pd.DataFrame(result)
    
    except Exception as e:
        logger.error(f"Erro ao buscar dados: {e}")
        return pd.DataFrame()

# ============================================================================
# CONTAGEM DE ATIVOS (VERDE/VERMELHA)
# ============================================================================

@st.cache_data(ttl=CACHE_TTL_SECONDS)
def contar_ativos(tickers_list, target_date_str, candle_ref, 
                  threshold=THRESHOLD_ATIVOS):
    """Conta quantos ativos estão subindo (acima do threshold)"""
    df = fetch_todos(tickers_list, target_date_str, candle_ref)
    
    if df.empty:
        return pd.Series(dtype=float)
    
    series_list = []
    
    for ticker in df.columns:
        try:
            s = df[ticker].dropna()
            
            if s.empty:
                continue
            
            abertura = float(s.values[0])
            
            if abertura == 0:
                continue
            
            pct = 100 * (df[ticker] - abertura) / abs(abertura)
            series_list.append(pct)
        
        except Exception:
            continue
    
    if not series_list:
        return pd.Series(dtype=float)
    
    return (pd.concat(series_list, axis=1) > threshold).sum(axis=1).astype(float)

# ============================================================================
# LINHA AZUL v2 (ÍNDICE COMPOSTO MACRO)
# ============================================================================

@st.cache_data(ttl=CACHE_TTL_SECONDS)
def fetch_linha_azul_v2(target_date_str, candle_ref):
    """
    Constrói a Linha Azul v2 como índice composto macro.
    
    Componentes:
    - USD/MXN (peso 2.0)
    - DXY (peso 1.5)
    - VIX (peso 1.2)
    - TNX (peso 1.3)
    - USD/ZAR (peso 0.9)
    
    Metodologia:
    1. Z-score rolling (janela 20)
    2. Ponderação com pesos
    3. Agregação
    4. EMA suave (length=10)
    """
    target = pd.Timestamp(target_date_str).date()
    
    try:
        # ====================================================================
        # 1. Baixar componentes
        # ====================================================================
        
        tickers = list(COMPONENTES_LINHA_AZUL.keys())
        df = fetch_todos(tickers, target_date_str, candle_ref)
        
        if df.empty:
            return pd.Series(dtype=float)
        
        # ====================================================================
        # 2. Calcular retorno percentual para cada ativo
        # ====================================================================
        
        scores = {}
        
        for ticker in tickers:
            try:
                serie = df[ticker].dropna()
                
                if len(serie) < 2:
                    continue
                
                # Retorno percentual desde abertura
                abertura = float(serie.iloc[0])
                
                if abertura == 0:
                    continue
                
                retorno_pct = ((serie - abertura) / abs(abertura)) * 100
                
                scores[ticker] = retorno_pct
            
            except Exception:
                continue
        
        if not scores:
            return pd.Series(dtype=float)
        
        # ====================================================================
        # 3. Normalizar com Z-score rolling
        # ====================================================================
        
        normalized_scores = {}
        
        for ticker, serie in scores.items():
            try:
                mean = serie.rolling(window=Z_SCORE_WINDOW, min_periods=1).mean()
                std = serie.rolling(window=Z_SCORE_WINDOW, min_periods=1).std()
                
                # Evitar divisão por zero
                std = std.replace(0, 1)
                
                z_score = (serie - mean) / std
                normalized_scores[ticker] = z_score
            
            except Exception:
                normalized_scores[ticker] = serie
        
        # ====================================================================
        # 4. Aplicar pesos
        # ====================================================================
        
        weighted_scores = {}
        total_weight = 0
        
        for ticker in tickers:
            if ticker in normalized_scores:
                peso = COMPONENTES_LINHA_AZUL[ticker]['peso']
                weighted_scores[ticker] = normalized_scores[ticker] * peso
                total_weight += peso
        
        if not weighted_scores:
            return pd.Series(dtype=float)
        
        # ====================================================================
        # 5. Agregar (média ponderada)
        # ====================================================================
        
        df_weighted = pd.DataFrame(weighted_scores)
        linha_azul_bruta = df_weighted.sum(axis=1) / total_weight
        
        # ====================================================================
        # 6. Suavizar com EMA
        # ====================================================================
        
        import pandas_ta as ta
        
        linha_azul_suave = ta.ema(linha_azul_bruta, 
                                   length=EMA_SMOOTHING_LENGTH)
        
        # Preenchimento de NaNs iniciais
        linha_azul_final = linha_azul_suave.fillna(method='bfill')
        
        return linha_azul_final.round(2)
    
    except Exception as e:
        logger.error(f"Erro ao calcular Linha Azul v2: {e}")
        return pd.Series(dtype=float)

# ============================================================================
# SCORE RORO (APETITE POR RISCO)
# ============================================================================

def fetch_roro_score(verde_count, vermelha_count):
    """Calcula RoRo score baseado em Verde/Vermelha"""
    try:
        if verde_count.empty or vermelha_count.empty:
            return pd.Series(dtype=float)
        
        den = (verde_count + vermelha_count).replace(0, np.nan)
        score_roro = (100 * (verde_count - vermelha_count) / den).fillna(0)
        
        return score_roro
    
    except Exception as e:
        logger.error(f"Erro ao calcular RoRo: {e}")
        return pd.Series(dtype=float)
