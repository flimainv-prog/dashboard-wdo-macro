# charts.py
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta
from config import BRT, logger

# ============================================================================
# CARDS DE STATUS
# ============================================================================

def render_status_cards(verde_atual, verm_atual, azul_v2_atual, spread, roro_atual):
    """Renderiza cards de status com valores atuais"""
    try:
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric(
                "🟢 Verde",
                f"{verde_atual:.0f}",
                delta=None,
                help="Quantidade de ativos em alta"
            )
        
        with col2:
            st.metric(
                "🔴 Vermelha",
                f"{verm_atual:.0f}",
                delta=None,
                help="Quantidade de ativos em baixa"
            )
        
        with col3:
            st.metric(
                "🔵 Azul v2",
                f"{azul_v2_atual:+.2f}",
                delta=None,
                help="Índice composto macro"
            )
        
        with col4:
            cor = "🟢" if spread > 0 else "🔴"
            st.metric(
                f"Spread {cor}",
                f"{spread:+.0f}",
                delta=None,
                help="Verde - Vermelha"
            )
        
        with col5:
            cor_roro = "📉" if roro_atual > 0 else "📈"
            st.metric(
                f"RoRo {cor_roro}",
                f"{roro_atual:+.0f}",
                delta=None,
                help="Apetite por risco"
            )
    
    except Exception as e:
        logger.error(f"Erro ao renderizar cards: {e}")

# ============================================================================
# GRÁFICO PRINCIPAL (RESPONSIVO)
# ============================================================================

def render_chart_wdo(chart_data, target_date, hora_inicio):
    """Renderiza gráfico principal responsivo"""
    try:
        # ====================================================================
        # Cálculos de eixo
        # ====================================================================
        
        azul_min = chart_data['Azul_v2'].min()
        azul_max = chart_data['Azul_v2'].max()
        r_abs = max(abs(azul_min), abs(azul_max), 20)
        y2_range = [-r_abs * 1.2, r_abs * 1.2]
        
        n_max = max(
            chart_data['Verde'].max(),
            chart_data['Vermelha'].max()
        )
        
        # ====================================================================
        # Criar figura
        # ====================================================================
        
        fig = go.Figure()
        
        # Linha zero
        fig.add_hline(
            y=0,
            line_color="rgba(0,100,255,0.5)",
            line_dash="dash",
            line_width=1.5,
            layer="below"
        )
        
        # ====================================================================
        # Traços
        # ====================================================================
        
        # Verde
        fig.add_trace(go.Scatter(
            x=chart_data.index,
            y=chart_data['Verde'],
            mode='lines+markers',
            name='🟢 Verde',
            line=dict(
                color='#00DD00',
                width=2.5,
                shape='linear'
            ),
            marker=dict(color='#00DD00', size=4, symbol='circle'),
            yaxis='y1',
            hovertemplate='%{y:.0f}<extra></extra>'
        ))
        
        # Vermelha
        fig.add_trace(go.Scatter(
            x=chart_data.index,
            y=chart_data['Vermelha'],
            mode='lines+markers',
            name='🔴 Vermelha',
            line=dict(
                color='#FF2222',
                width=2.5,
                shape='linear'
            ),
            marker=dict(color='#FF2222', size=4, symbol='circle'),
            yaxis='y1',
            hovertemplate='%{y:.0f}<extra></extra>'
        ))
        
        # Azul v2
        fig.add_trace(go.Scatter(
            x=chart_data.index,
            y=chart_data['Azul_v2'],
            customdata=chart_data['Azul_v2'].values,
            mode='lines+markers',
            name='🔵 Azul v2',
            line=dict(
                color='#0066FF',
                width=2.5,
                shape='linear'
            ),
            marker=dict(color='#0066FF', size=4, symbol='circle'),
            yaxis='y2',
            hovertemplate='%{customdata:+.2f} pts<extra></extra>'
        ))
        
        # ====================================================================
        # Grid
        # ====================================================================
        
        for level in range(0, int(n_max) + 5, 5):
            fig.add_hline(
                y=level,
                line_dash="dashdot",
                line_color="lightgray",
                opacity=0.3,
                layer="below"
            )
        
        # ====================================================================
        # Layout Responsivo
        # ====================================================================
        
        x_inicio = pd.Timestamp(f"{target_date} {hora_inicio:02d}:00", tz=BRT)
        agora = datetime.now(BRT)
        
        if target_date == agora.date():
            from data_sources import ultimo_candle_real
            x_fim = ultimo_candle_real() + timedelta(minutes=15)
        else:
            x_fim = pd.Timestamp(f"{target_date} 23:50", tz=BRT) + timedelta(minutes=15)
        
        fig.update_layout(
            title=f"📈 Dashboard Macro WDO | {target_date.strftime('%d/%m/%Y')}",
            height=600,
            dragmode=False,
            xaxis=dict(
                title=None,
                range=[x_inicio, x_fim],
                tickformat="%H:%M",
                fixedrange=True
            ),
            yaxis=dict(
                title="Verde/Vermelha",
                range=[0, n_max + 2],
                tickmode='linear',
                dtick=5,
                gridcolor='lightgray',
                gridwidth=1,
                side='left',
                fixedrange=True
            ),
            yaxis2=dict(
                title="Azul v2 (pts)",
                overlaying='y',
                side='right',
                range=y2_range,
                dtick=10,
                showgrid=False,
                zeroline=False,
                fixedrange=True
            ),
            template="plotly_white",
            showlegend=True,
            hovermode='x unified',
            hoverlabel=dict(bgcolor="white", font_size=12),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.12,
                xanchor="center",
                x=0.5
            ),
            margin=dict(l=80, r=80, t=60, b=60)
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    except Exception as e:
        logger.error(f"Erro ao renderizar gráfico: {e}")
        st.error("Erro ao renderizar gráfico")

# ============================================================================
# INFO BOX
# ============================================================================

def render_info_box(sinal, prev_direcao, prev_prob, vix_atual, regime):
    """Renderiza info box com sinais e previsão"""
    try:
        if sinal == "COMPRA":
            st.success(f"🟢 **SINAL DE COMPRA** | Regime: {regime}")
        elif sinal == "VENDA":
            st.error(f"🔴 **SINAL DE VENDA** | Regime: {regime}")
        else:
            st.warning(f"🟡 **AGUARDAR** | Regime: {regime}")
        
        if prev_direcao:
            if prev_direcao == "ALTA":
                st.info(f"🔮 Próximo candle: **⬆️ ALTA** ({prev_prob:.0f}%)")
            elif prev_direcao == "BAIXA":
                st.info(f"🔮 Próximo candle: **⬇️ BAIXA** ({prev_prob:.0f}%)")
            else:
                st.info(f"🔮 Próximo candle: **➡️ NEUTRO**")
    
    except Exception as e:
        logger.error(f"Erro ao renderizar info box: {e}")
