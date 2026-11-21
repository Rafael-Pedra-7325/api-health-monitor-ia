import os
import requests
import streamlit as st

GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"


def _obter_api_key(chave_manual: str = "") -> str:
    if chave_manual.strip():
        return chave_manual.strip()
    if "GEMINI_API_KEY" in st.secrets:
        return str(st.secrets["GEMINI_API_KEY"]).strip()
    return os.getenv("GEMINI_API_KEY", "").strip()


def _diagnostico_fallback(status_code: int, latencia_ms: float, detalhe_erro: str) -> str:
    if status_code == 0:
        return f"Causa: Falha de conexão/DNS ({detalhe_erro}). Ação: Validar conectividade de rede, certificado SSL e disponibilidade do host."
    if status_code == 429:
        return "Causa: Rate Limit atingido (HTTP 429). Ação: Implementar fila de requisições, cache semântico/local e backoff exponencial."
    if status_code >= 500:
        return f"Causa: Erro interno no servidor de destino (HTTP {status_code}). Ação: Ativar Circuit Breaker e redirecionar para rota de contingência."
    if status_code >= 400:
        return f"Causa: Erro na requisição do cliente (HTTP {status_code}). Ação: Revisar autenticação (tokens/headers) e parâmetros enviados no payload."
    return f"Causa: Degradação de performance ({latencia_ms:.0f} ms). Ação: Investigar gargalos de rede ou aplicar cache nas respostas."


def gerar_diagnostico_ia(
    servico: str,
    url: str,
    status_code: int,
    latencia_ms: float,
    resposta_trecho: str,
    chave_manual: str = "",
) -> tuple[str, str]:
    """Retorna (texto_diagnostico, modo_execucao)."""
    api_key = _obter_api_key(chave_manual)

    if not api_key:
        return _diagnostico_fallback(status_code, latencia_ms, resposta_trecho), "Fallback Local (sem API Key)"

    prompt = (
        "Você é um Engenheiro de Confiabilidade (SRE). Analise o incidente de API abaixo "
        "e responda em português de forma direta, em no máximo 2 frases curtas seguindo o formato "
        "'Causa: ... Ação: ...'.\n\n"
        f"- Serviço: {servico}\n"
        f"- URL: {url}\n"
        f"- Status HTTP: {status_code}\n"
        f"- Latência: {latencia_ms:.2f} ms\n"
        f"- Trecho da resposta/erro: {resposta_trecho[:300]}"
    )

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 500,
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }

    try:
        resp = requests.post(
            f"{GEMINI_ENDPOINT}?key={api_key}",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=15,
        )
        if resp.status_code != 200:
            return _diagnostico_fallback(status_code, latencia_ms, resposta_trecho), f"Fallback Local (HTTP {resp.status_code})"

        data = resp.json()
        partes = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
        texto = "".join(p.get("text", "") for p in partes).strip()

        if not texto:
            return _diagnostico_fallback(status_code, latencia_ms, resposta_trecho), "Fallback Local (resposta vazia)"

        return texto, "Gemini 2.5 Flash (API REST)"
    except Exception as exc:
        return _diagnostico_fallback(status_code, latencia_ms, resposta_trecho), f"Fallback Local ({type(exc).__name__})"
