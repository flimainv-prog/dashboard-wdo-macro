# indicators.py
import pandas as pd
import numpy as np

import json
from config import (
    RSI_LENGTH, PESOS_SCORE, THRESHOLD_ALTA, 
    THRESHOLD_BAIXA, logger
)

# ============================================================================
# RSI (Cálculo Manual)
# ============================================================================

def calcular_rsi(serie, length=RSI_LENGTH):
    """Calcula RSI manualmente"""
    try:
        if len(serie) < length:
            return None
        
        delta = serie.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=length).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=length).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return float(rsi.iloc[-1])
    
    except Exception:
        return None

# ============================================================================
# MOMENTUM
# ============================================================================

def calcular_momentum(serie, periodo=4):
    """Calcula momentum simples (mudança em N períodos)"""
    try:
        if len(serie) < periodo:
            return 0.0
        
        momentum = (serie.iloc[-1] - serie.iloc[-periodo]) / periodo
        return float(momentum)
    
    except Exception:
        return 0.0

# ============================================================================
# TENDÊNCIA
# ============================================================================

def calcular_tendencia(serie, periodo_curto=3, periodo_longo=6):
    """Calcula tendência comparando médias móveis"""
    try:
        if len(serie) < periodo_longo:
            return 0.0
        
        media_curta = serie.iloc[-periodo_curto:].mean()
        media_longa = serie.iloc[-periodo_longo:-periodo_curto].mean()
        
        tendencia = media_curta - media_longa
        return float(tendencia)
    
    except Exception:
        return 0.0

# ============================================================================
# SCORE BUILDER (SCORE COMPOSTO)
# ============================================================================

def score_builder(rsi, momentum, tendencia, roro):
    """
    Constrói score ponderado para previsão.
    
    Pesos:
    - RSI: 60%
    - Momentum: 20%
    - Tendência: 15%
    - RoRo: 5%
    """
    try:
        score = 50.0  # Neutro
        
        # RSI (60%)
        if rsi is not None:
            if rsi > 60:
                score += (rsi - 60) * PESOS_SCORE['rsi'] * 0.8
            elif rsi < 40:
                score -= (40 - rsi) * PESOS_SCORE['rsi'] * 0.8
        
        # Momentum (20%)
        score += np.clip(momentum * PESOS_SCORE['momentum'] * 2, -15, 15)
        
        # Tendência (15%)
        score += np.clip(tendencia * PESOS_SCORE['tendencia'] * 1.5, -10, 10)
        
        # RoRo (5%)
        if abs(roro) > 5:
            score += np.clip((roro / 100) * PESOS_SCORE['roro'] * 100, -5, 5)
        
        return float(np.clip(score, 5, 95))
    
    except Exception as e:
        logger.warning(f"Erro ao calcular score: {e}")
        return 50.0

# ============================================================================
# PREVISÃO DO PRÓXIMO CANDLE v2
# ============================================================================

def prever_candle_v2(chart_data_json, spread):
    """
    Previsão de próximo candle baseada em:
    - RSI da Linha Azul v2
    - Momentum
    - Tendência
    - Spread Verde/Vermelha
    - RoRo
    """
    try:
        chart_data = pd.read_json(chart_data_json)
        
        # Extrai Linha Azul v2
        if 'Azul_v2' not in chart_data.columns:
            return None
        
        azul = chart_data['Azul_v2'].dropna()
        
        if len(azul) < 14:
            return None
        
        # ====================================================================
        # Cálculos
        # ====================================================================
        
        rsi = calcular_rsi(azul, length=RSI_LENGTH)
        momentum = calcular_momentum(azul, periodo=4)
        tendencia = calcular_tendencia(azul, periodo_curto=3, periodo_longo=6)
        
        # RoRo (se existir na tabela)
        roro = 0.0
        if 'RoRo' in chart_data.columns:
            roro = float(chart_data['RoRo'].iloc[-1])
        
        # ====================================================================
        # Score Composto
        # ====================================================================
        
        score = score_builder(rsi, momentum, tendencia, roro)
        
        # ====================================================================
        # Ajuste por Spread
        # ====================================================================
        
        if spread > 3:
            score += 10
        elif spread < -3:
            score -= 10
        
        score = float(np.clip(score, 5, 95))
        
        # ====================================================================
        # Decisão
        # ====================================================================
        
        if score >= THRESHOLD_ALTA:
            return ("ALTA", score, "⬆️")
        elif score <= THRESHOLD_BAIXA:
            return ("BAIXA", 100 - score, "⬇️")
        else:
            return ("NEUTRO", 50.0, "➡️")
    
    except Exception as e:
        logger.error(f"Erro ao prever candle: {e}")
        return None

# ============================================================================
# DETECÇÃO DE DIVERGÊNCIAS
# ===================================================================
