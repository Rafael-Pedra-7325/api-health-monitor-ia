import sqlite3
from datetime import datetime, timedelta
import random

DB_PATH = "monitor_apis.db"

QUERY_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS api_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    servico TEXT NOT NULL,
    url TEXT NOT NULL,
    status_code INTEGER NOT NULL,
    latencia_ms REAL NOT NULL,
    sucesso INTEGER NOT NULL,
    diagnostico_ia TEXT,
    criado_em TEXT NOT NULL
);
"""

QUERY_METRICAS_POR_SERVICO = """
SELECT 
    servico,
    COUNT(*) AS total_checks,
    ROUND(AVG(latencia_ms), 2) AS latencia_media_ms,
    ROUND(SUM(sucesso) * 100.0 / COUNT(*), 1) AS disponibilidade_pct
FROM api_logs
GROUP BY servico
ORDER BY disponibilidade_pct ASC, latencia_media_ms DESC;
"""

QUERY_HISTORICO_RECENTE = """
SELECT 
    criado_em AS "Data/Hora",
    servico AS "Serviço",
    status_code AS "Status HTTP",
    latencia_ms AS "Latência (ms)",
    CASE WHEN sucesso = 1 THEN 'Online' ELSE 'Incidente' END AS "Estado",
    COALESCE(diagnostico_ia, 'Operação normal') AS "Diagnóstico IA"
FROM api_logs
ORDER BY id DESC
LIMIT 25;
"""


def get_connection():
    return sqlite3.connect(DB_PATH)


def inicializar_banco():
    with get_connection() as conn:
        conn.execute(QUERY_CREATE_TABLE)
        cursor = conn.execute("SELECT COUNT(*) FROM api_logs")
        total = cursor.fetchone()[0]

        # Popula com histórico realista na primeira execução para demonstração imediata
        if total == 0:
            exemplos = [
                ("ViaCEP API", "https://viacep.com.br/ws/01001000/json/", 200, 142.5, 1, None),
                ("GitHub API", "https://api.github.com/zen", 200, 210.3, 1, None),
                ("JSONPlaceholder", "https://jsonplaceholder.typicode.com/posts/1", 200, 98.7, 1, None),
                (
                    "Gateway Pagamentos (Simulado)",
                    "https://httpbin.org/status/503",
                    503,
                    1240.0,
                    0,
                    "Causa: Serviço indisponível (HTTP 503 - sobrecarga ou manutenção no upstream). Ação: Ativar fallback e aplicar retry com backoff exponencial.",
                ),
                ("ViaCEP API", "https://viacep.com.br/ws/01001000/json/", 200, 155.1, 1, None),
                (
                    "API Parceiro (Rate Limit)",
                    "https://httpbin.org/status/429",
                    429,
                    310.4,
                    0,
                    "Causa: Limite de requisições excedido (HTTP 429 - Too Many Requests). Ação: Implementar cache local e respeitar o cabeçalho Retry-After.",
                ),
            ]
            agora = datetime.now()
            for idx, (servico, url, status, lat, ok, diag) in enumerate(exemplos):
                ts = (agora - timedelta(minutes=(len(exemplos) - idx) * 15)).strftime("%Y-%m-%d %H:%M:%S")
                conn.execute(
                    """
                    INSERT INTO api_logs (servico, url, status_code, latencia_ms, sucesso, diagnostico_ia, criado_em)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (servico, url, status, lat + random.uniform(-10, 15), ok, diag, ts),
                )
        conn.commit()


def registrar_check(servico: str, url: str, status_code: int, latencia_ms: float, sucesso: bool, diagnostico_ia: str | None):
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO api_logs (servico, url, status_code, latencia_ms, sucesso, diagnostico_ia, criado_em)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (servico, url, status_code, round(latencia_ms, 2), int(sucesso), diagnostico_ia, agora),
        )
        conn.commit()


def obter_metricas_sql():
    with get_connection() as conn:
        return conn.execute(QUERY_METRICAS_POR_SERVICO).fetchall()


def obter_historico_sql():
    with get_connection() as conn:
        cursor = conn.execute(QUERY_HISTORICO_RECENTE)
        colunas = [desc[0] for desc in cursor.description]
        dados = cursor.fetchall()
        return colunas, dados
