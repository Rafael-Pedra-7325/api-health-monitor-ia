import time
import requests
import pandas as pd
import streamlit as st

from database import (
    inicializar_banco,
    registrar_check,
    obter_metricas_sql,
    obter_historico_sql,
    QUERY_CREATE_TABLE,
    QUERY_METRICAS_POR_SERVICO,
    QUERY_HISTORICO_RECENTE,
)
from ai_diagnostico import gerar_diagnostico_ia

st.set_page_config(page_title="API Health Monitor + IA", page_icon="📡", layout="wide")
inicializar_banco()

PRESETS = {
    "ViaCEP API (Saudável)": ("ViaCEP API", "https://viacep.com.br/ws/01001000/json/"),
    "GitHub Zen API (Saudável)": ("GitHub API", "https://api.github.com/zen"),
    "Simular Erro 503 (Indisponível)": ("Gateway Pagamentos (Simulado)", "https://httpbin.org/status/503"),
    "Simular Erro 429 (Rate Limit)": ("API Parceiro (Rate Limit)", "https://httpbin.org/status/429"),
    "Simular Lentidão (2.5s Delay)": ("Serviço Legado Lento", "https://httpbin.org/delay/2"),
    "URL Personalizada": ("Serviço Customizado", ""),
}

st.title("📡 Monitor de APIs REST com Diagnóstico por IA")
st.caption("Observabilidade de endpoints em Python + SQLite (SQL) + diagnóstico automatizado de incidentes com LLM.")

# Sidebar de Configuração e Testes Rápidos
with st.sidebar:
    st.header("⚡ Teste Rápido (1 Clique)")
    opcao = st.selectbox("Escolha um cenário de teste:", list(PRESETS.keys()))
    nome_padrao, url_padrao = PRESETS[opcao]

    servico_input = st.text_input("Nome do Serviço", value=nome_padrao)
    url_input = st.text_input("Endpoint (URL)", value=url_padrao, placeholder="https://...")
    limiar_ms = st.slider("Alerta de lentidão (ms)", min_value=300, max_value=3000, value=1200, step=100)

    st.divider()
    api_key_usuario = st.text_input(
        "Gemini API Key (opcional)",
        type="password",
        help="Se deixado em branco, usa a chave configurada no servidor ou o motor de fallback.",
    )

# Execução do Health Check
col_btn, col_info = st.columns([1, 3])
with col_btn:
    executar = st.button("🚀 Executar Health Check", type="primary", use_container_width=True)

if executar:
    if not url_input.strip():
        st.warning("Informe uma URL válida para testar.")
    else:
        with st.spinner(f"Consultando {servico_input}..."):
            inicio = time.perf_counter()
            try:
                resp = requests.get(url_input.strip(), timeout=8)
                latencia_ms = (time.perf_counter() - inicio) * 1000
                status_code = resp.status_code
                trecho_resposta = resp.text[:300]
            except requests.RequestException as exc:
                latencia_ms = (time.perf_counter() - inicio) * 1000
                status_code = 0
                trecho_resposta = str(exc)

            saudavel = (200 <= status_code < 400) and (latencia_ms <= limiar_ms)
            diagnostico = None
            modo_ia = None

            if not saudavel:
                diagnostico, modo_ia = gerar_diagnostico_ia(
                    servico=servico_input,
                    url=url_input,
                    status_code=status_code,
                    latencia_ms=latencia_ms,
                    resposta_trecho=trecho_resposta,
                    chave_manual=api_key_usuario,
                )

            registrar_check(
                servico=servico_input,
                url=url_input,
                status_code=status_code,
                latencia_ms=latencia_ms,
                sucesso=saudavel,
                diagnostico_ia=diagnostico,
            )

        if saudavel:
            st.success(f"**{servico_input} Online** — HTTP `{status_code}` em `{latencia_ms:.0f} ms`. Registro salvo no SQLite.")
        else:
            st.error(f"**Incidente Detectado em {servico_input}** — HTTP `{status_code}` | Latência: `{latencia_ms:.0f} ms`")
            st.info(f"🤖 **Diagnóstico SRE ({modo_ia}):** {diagnostico}")

st.divider()

# Painel Analítico via Consultas SQL
metricas = obter_metricas_sql()
colunas_hist, dados_hist = obter_historico_sql()
df_metricas = pd.DataFrame(metricas, columns=["Serviço", "Total Checks", "Latência Média (ms)", "Disponibilidade (%)"])
df_historico = pd.DataFrame(dados_hist, columns=colunas_hist)

kpi1, kpi2, kpi3 = st.columns(3)
kpi1.metric("Total de Monitoramentos (SQL)", int(df_metricas["Total Checks"].sum()))
kpi2.metric("Disponibilidade Média", f"{df_metricas['Disponibilidade (%)'].mean():.1f}%")
kpi3.metric("Latência Média Global", f"{df_metricas['Latência Média (ms)'].mean():.0f} ms")

col_esq, col_dir = st.columns(2)
with col_esq:
    st.subheader("📊 Disponibilidade por Serviço (%)")
    st.bar_chart(df_metricas.set_index("Serviço")["Disponibilidade (%)"])

with col_dir:
    st.subheader("⏱️ Latência Média por Serviço (ms)")
    st.bar_chart(df_metricas.set_index("Serviço")["Latência Média (ms)"])

st.subheader("🗄️ Histórico Recente de Execuções & Diagnósticos")
st.dataframe(df_historico, use_container_width=True, hide_index=True)

# Transparência Técnica para Entrevistas
with st.expander("🔍 Por baixo dos panos: Modelagem e Consultas SQL Executadas"):
    st.markdown("**1. DDL — Estrutura da Tabela (`api_logs`):**")
    st.code(QUERY_CREATE_TABLE.strip(), language="sql")
    st.markdown("**2. DQL — Agregação de Disponibilidade e Latência (`GROUP BY`):**")
    st.code(QUERY_METRICAS_POR_SERVICO.strip(), language="sql")
    st.markdown("**3. DQL — Consulta de Histórico Recente:**")
    st.code(QUERY_HISTORICO_RECENTE.strip(), language="sql")
