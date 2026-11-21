import os
import requests
import streamlit as st

BASE_URL = "https://generativelanguage.googleapis.com/v1beta"


def _obter_api_key(chave_manual: str = "") -> str:
    if chave_manual.strip():
        return chave_manual.strip()
    if "GEMINI_API_KEY" in st.secrets:
        return str(st.secrets["GEMINI_API_KEY"]).strip()
    return os.getenv("GEMINI_API_KEY", "").strip()


def _listar_modelos_disponiveis(api_key: str) -> list[str]:
    """Consulta o catálogo da API para descobrir modelos Flash ativos."""
    modelos_padrao = ["models/gemini-flash-latest", "models/gemini-2.5-flash", "models/gemini-2.0-flash"]
    try:
        resp = requests.get(f"{BASE_URL}/models?key={api_key}", timeout=8)
        if resp.status_code == 200:
            dados = resp.json().get("models", [])
            descobertos = [
                m["name"]
                for m in dados
                if "generateContent" in m.get("supportedGenerationMethods", [])
                and "flash" in m.get("name", "").lower()
                and not any(x in m["name"].lower() for x in ["image", "audio", "tts", "live", "embedding"])
            ]
            if descobertos:
                return descobertos
    except Exception:
        pass
    return modelos_padrao


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
            "maxOutputTokens": 800,
        },
    }

    modelos = _listar_modelos_disponiveis(api_key)
    ultimo_status = "erro de rede"

    for modelo in modelos[:3]:
        try:
            resp = requests.post(
                f"{BASE_URL}/{modelo}:generateContent?key={api_key}",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json()
                partes = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
                texto = "".join(p.get("text", "") for p in partes).strip()
                if texto:
                    nome_limpo = modelo.replace("models/", "")
                    return texto, f"{nome_limpo} (API REST)"
            ultimo_status = f"HTTP {resp.status_code}"
        except Exception as exc:
            ultimo_status = type(exc).__name__

    return _diagnostico_fallback(status_code, latencia_ms, resposta_trecho), f"Fallback Local ({ultimo_status})"
