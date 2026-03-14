# signals.py
import pandas as pd
import os
from datetime import datetime
from config import (
    BRT, LOG_FILE, SPREAD_COMPRA, SPREAD_VENDA,
    RORO_COMPRA, RORO_VENDA, VIX_CALMO, VIX_NORMAL,
    VIX_MODERADO, VIX_ALTO, logger
)

# ============================================================================
# LOGGING DE SINAIS
# ============================================================================

def log_signal(ts, target_date, hora_inicio, verde_atual, verm_atual,
               spread, roro_atual, rastro_antigo, azul_v2_atual, 
               sinal, prev_direcao, prev_prob):
    """Registra sinais em CSV para análise histórica"""
    try:
        row = {
            "timestamp": ts.isoformat(),
            "data_ref": str(target_date),
            "hora_inicio": hora_inicio,
            "verde": float(verde_atual),
            "vermelha": float(verm_atual),
            "spread": float(spread),
            "roro": float(roro_atual),
            "azul_v1": float(rastro_antigo),
            "azul_v2": float(azul_v2_atual),
            "sinal": sinal,
            "prev_direcao": prev_direcao or "",
            "prev_prob": float(prev_prob) if prev_prob is not None else ""
        }
        
        df_row = pd.DataFrame([row])
        
        if os.path.exists(LOG_FILE):
            df_row.to_csv(LOG_FILE, mode="a", header=False, index=False)
        else:
            df_row.to_csv(LOG_FILE, mode="w", header=True, index=False)
        
        logger.info(f"Sinal registrado: {sinal} | Spread: {spread:.0f}")
    
    except Exception as e:
        logger.error(f"Erro ao registrar sinal: {e}")

# ============================================================================
# GERAÇÃO DE SINAIS
# ============================================================================

def gerar_sinal_compra_venda(verde_atual, verm_atual, spread):
    """Gera sinal baseado no spread Verde/Vermelha"""
    try:
        if spread > SPREAD_COMPRA:
            return ("COMPRA", "🟢", "success")
        elif spread < SPREAD_VENDA:
            return ("VENDA", "🔴", "error")
        else:
            return ("AGUARDAR", "🟡", "warning")
    
    except Exception as e:
        logger.error(f"Erro ao gerar sinal: {e}")
        return ("ERRO", "❌", "error")

# ============================================================================
# VALIDAÇÃO DE LEILÃO (08:55-09:00)
# ============================================================================

def validar_leilao(verde_count, vermelha_count, target_date, ts_855):
    """
    Valida se leilão está habilitado.
    Leilão habilitado se |Verde - Vermelha| > 8 em 08:55
    """
    try:
        diff = 0
        
        if not verde_count.empty:
            dados_verde = verde_count[verde_count.index <= ts_855]
            if not dados_verde.empty:
                diff = abs(dados_verde.iloc[-1])
        
        if not vermelha_count.empty:
            dados_verm = vermelha_count[vermelha_count.index <= ts_855]
            if not dados_verm.empty:
                diff = abs(dados_verm.iloc[-1])
        
        if diff and diff > 8:
            return True
        
        return False
    
    except Exception as e:
        logger.warning(f"Erro ao validar leilão: {e}")
        return False

# ============================================================================
# CLASSIFICAÇÃO DE REGIME (VIX)
# ============================================================================

def get_regime_mercado(vix_atual):
    """Classifica o regime de mercado baseado no VIX"""
    try:
        if vix_atual is None:
            return "❓ Desconhecido"
        
        if vix_atual < VIX_CALMO:
            return "🟢 Calmo"
        elif vix_atual < VIX_NORMAL:
            return "🟡 Normal"
        elif vix_atual < VIX_MODERADO:
            return "🟠 Moderado"
        elif vix_atual < VIX_ALTO:
            return "🔴 Alto"
        else:
            return "🚨 Extremo"
    
    except Exception:
        return "❓ Desconhecido"

# ============================================================================
# LABELS DE RORO
# ============================================================================

def gerar_label_roro(roro_atual):
    """Gera label descritivo para RoRo"""
    try:
        if roro_atual > RORO_COMPRA:
            return "📉 Dólar comprador — COMPRA WDO"
        elif roro_atual < RORO_VENDA:
            return "📈 Dólar vendedor — VENDA WDO"
        else:
            return "➡️ Neutro"
    
    except Exception:
        return "➡️ Neutro"

# ============================================================================
# CARREGAMENTO DE HISTÓRICO
# ============================================================================

def load_historico_sinais():
    """Carrega histórico de sinais do CSV"""
    try:
        if not os.path.exists(LOG_FILE):
            return pd.DataFrame()
        
        df = pd.read_csv(LOG_FILE)
        
        # Converte timestamp para datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Ordena por timestamp descendente
        df = df.sort_values('timestamp', ascending=False)
        
        return df
    
    except Exception as e:
        logger.error(f"Erro ao carregar histórico: {e}")
        return pd.DataFrame()
