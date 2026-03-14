# app.py
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime


# Importa todos os módulos
from config import BRT, AUTO_REFRESH_INTERVAL_MS, CACHE_TTL_SECONDS, get_feriados_br
from data_sources import (
    get_vix, get_wdo_dates, contar_ativos, fetch_linha_azul_v2, 
    fetch_roro_score, ultimo_candle_real, ATIVOS_VERDE, ATIVOS_VERMELHA
)
from indicators import prever_candle_v2
from signals import (
    log_signal, gerar_sinal_compra_venda, validar_leilao,
    get_regime_mercado, gerar_label_roro, load_historico_sinais
)
from charts import render_chart_wdo, render_status_cards, render_info_box

# ============================================================================
# CONFIGURAÇÃO STREAMLIT
# ============================================================================

st.set_page_config(
    page_title="Dashboard WDO Macro",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# AUTO-REFRESH (5 minutos)
# ============================================================================



st.title("🟢🔴 Dashboard WDO Macro v2")


# ============================================================================
# SIDEBAR - CONTROLES
# ============================================================================

with st.sidebar:
    st.subheader("⚙️ Controles")
    
    # VIX e Regime
    vix_atual = get_vix()
    if vix_atual is not None:
        regime = get_regime_mercado(vix_atual)
        st.info(f"📊 VIX: **{vix_atual:.1f}** — {regime}")
    
    # Data
    wdo_dates = get_wdo_dates()
    target_date = st.selectbox(
        "📅 Selecione a Data (WDOFUT):",
        wdo_dates,
        format_func=lambda d: d.strftime("%d/%m/%Y (%a)"),
        index=0
    )
    
    # Hora de início
    hora_inicio = st.selectbox(
        "🕐 Gráfico inicia às:",
        options=list(range(0, 24)),
        format_func=lambda h: f"{h:02d}:00",
        index=2
    )
    
    # Botão de refresh
    if st.button("🔄 Atualizar agora"):
        st.cache_data.clear()
        st.rerun()

# ============================================================================
# VALIDAÇÃO DE DATA
# ============================================================================

feriados = get_feriados_br()
dia_semana = target_date.weekday()

if dia_semana >= 5:
    st.info(f"🔒 Mercado fechado — {target_date.strftime('%d/%m/%Y')} é " +
            f"{'sábado' if dia_semana == 5 else 'domingo'}.")
    st.stop()

if str(target_date) in feriados:
    st.info(f"🔒 Mercado fechado — {target_date.strftime('%d/%m/%Y')} é feriado nacional.")
    st.stop()

# ============================================================================
# COLETA DE DADOS
# ============================================================================

agora_ciclo = datetime.now(BRT)
candle_ref = agora_ciclo.replace(
    minute=(agora_ciclo.minute // 5) * 5,
    second=0, microsecond=0,
).isoformat()

# Verifica cache com params
params_hash = f"{target_date}_{candle_ref}"

if "last_params" not in st.session_state:
    st.session_state.last_params = None

if st.session_state.last_params != params_hash:
    with st.spinner("⏳ Carregando dados de mercado..."):
        verde_count = contar_ativos(ATIVOS_VERDE, str(target_date), candle_ref)
        vermelha_count = contar_ativos(ATIVOS_VERMELHA, str(target_date), candle_ref)
        linha_azul_v2 = fetch_linha_azul_v2(str(target_date), candle_ref)
        
        st.session_state.verde_count = verde_count
        st.session_state.vermelha_count = vermelha_count
        st.session_state.linha_azul_v2 = linha_azul_v2
        st.session_state.last_params = params_hash
else:
    verde_count = st.session_state.verde_count
    vermelha_count = st.session_state.vermelha_count
    linha_azul_v2 = st.session_state.linha_azul_v2

# ============================================================================
# CÁLCULO DE RoRo
# ============================================================================

score_roro = fetch_roro_score(verde_count, vermelha_count)

# ============================================================================
# CONSOLIDAÇÃO DE DADOS
# ============================================================================

if not verde_count.empty and not vermelha_count.empty and not linha_azul_v2.empty:
    common_idx = (
        verde_count.index
        .intersection(vermelha_count.index)
        .intersection(linha_azul_v2.index)
    )
    
    chart_data = pd.DataFrame({
        'Verde': verde_count[common_idx],
        'Vermelha': vermelha_count[common_idx],
        'Azul_v2': linha_azul_v2[common_idx]
    }).dropna()
    
    if not score_roro.empty:
        chart_data['RoRo'] = score_roro.reindex(chart_data.index).fillna(0)
    
    # Filtro de hora
    hora_filtro = pd.Timestamp(f"{target_date} {hora_inicio:02d}:00", tz=BRT)
    chart_data = chart_data[chart_data.index >= hora_filtro]
    
    # Filtro de data atual
    if target_date == datetime.now(BRT).date():
        chart_data = chart_data[chart_data.index <= ultimo_candle_real()]
    
    if chart_data.empty:
        st.warning("⚠️ Ainda sem candles para este horário.")
        st.stop()
    
    # ============================================================================
    # VALORES ATUAIS
    # ============================================================================
    
    verde_atual = chart_data['Verde'].iloc[-1]
    verm_atual = chart_data['Vermelha'].iloc[-1]
    azul_v2_atual = chart_data['Azul_v2'].iloc[-1]
    spread = float(verde_atual - verm_atual)
    roro_atual = float(chart_data['RoRo'].iloc[-1]) if 'RoRo' in chart_data.columns else 0.0
    
    # ============================================================================
    # GERAÇÃO DE SINAIS
    # ============================================================================
    
    sinal, emoji, cor = gerar_sinal_compra_venda(verde_atual, verm_atual, spread)
    prev = prever_candle_v2(chart_data.to_json(), spread)
    
    prev_direcao = None
    prev_prob = None
    if prev:
        prev_direcao, prev_prob, emoji_prev = prev
    
    # ============================================================================
    # VALIDAÇÃO DE LEILÃO (08:55-09:00)
    # ============================================================================
    
    agora = datetime.now(BRT)
    if target_date == agora.date() and (
        agora.replace(hour=8, minute=55, second=0, microsecond=0) <= agora <
        agora.replace(hour=9, minute=0, second=0, microsecond=0)
    ):
        ts_855 = pd.Timestamp(f"{target_date} 08:55", tz=BRT)
        leilao_ok = validar_leilao(verde_count, vermelha_count, target_date, ts_855)
        if leilao_ok:
            st.error("🔨 LEILÃO HABILITADO")
        else:
            st.info("🔨 LEILÃO NÃO HABILITADO")
    
    # ============================================================================
    # LOGGING
    # ============================================================================
    
    ultima_ts = chart_data.index[-1]
    if "last_logged_ts" not in st.session_state:
        st.session_state.last_logged_ts = None
    
    if st.session_state.last_logged_ts != ultima_ts:
        log_signal(
            ultima_ts, target_date, hora_inicio,
            verde_atual, verm_atual, spread,
            roro_atual, 0.0, azul_v2_atual, sinal,
            prev_direcao, prev_prob
        )
        st.session_state.last_logged_ts = ultima_ts
    
    # ============================================================================
    # RENDERIZAÇÃO
    # ============================================================================
    
    # Cards de Status
    render_status_cards(verde_atual, verm_atual, azul_v2_atual, spread, roro_atual)
    
    st.divider()
    
    # Gráfico Principal
    render_chart_wdo(chart_data, target_date, hora_inicio)
    
    st.divider()
    
    # Info Box
    regime = get_regime_mercado(vix_atual)
    render_info_box(sinal, prev_direcao, prev_prob, vix_atual if vix_atual else 0, regime)
    
    # ============================================================================
    # HISTÓRICO (BONUS)
    # ============================================================================
    
    st.divider()
    
    with st.expander("📋 Ver Histórico de Sinais"):
        df_historico = load_historico_sinais()
        if not df_historico.empty:
            st.dataframe(df_historico.tail(20), use_container_width=True)
        else:
            st.info("Nenhum histórico registrado ainda.")

else:
    st.warning("⚠️ Dados insuficientes para análise.")
