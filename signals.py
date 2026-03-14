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

# ==========================
