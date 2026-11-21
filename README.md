[![Live Demo](https://img.shields.io/badge/Live_Demo-Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://api-health-monitor-ia.streamlit.app/)
# 📡 API Health Monitor + IA

Monitor de disponibilidade e latência de APIs REST construído em **Python**, **SQL (SQLite)** e **Streamlit**, com diagnóstico automático de incidentes utilizando **IA Generativa (Gemini REST API)**.

## 🎯 Problema Resolvido (Dor Real)
Quando integrações externas sofrem degradação de latência ou retornam códigos HTTP de erro (`429`, `500`, `503`), equipes técnicas perdem tempo investigando causas genéricas e registrando ocorrências manualmente. Este projeto automatiza:
1. O monitoramento ativo de endpoints REST (status HTTP e tempo de resposta em `ms`);
2. A persistência e agregação analítica de métricas em banco relacional **SQL**;
3. A geração automática de causa raiz e plano de ação via **LLM** sempre que um incidente é detectado.

## 🛠️ Tecnologias Utilizadas
* **Linguagem & Interface:** Python, Streamlit, Pandas
* **Banco de Dados:** SQLite com consultas SQL puras (`DDL`, `DML`, `GROUP BY`, agregações)
* **Integrações:** Consumo de APIs REST (`requests`) e Google Gemini API (`gemini-2.5-flash`)

## 🚀 Como Executar Localmente
```bash
git clone [https://github.com/Rafael-Pedra-7325/api-health-monitor-ia.git](https://github.com/Rafael-Pedra-7325/api-health-monitor-ia.git)
cd api-health-monitor-ia
pip install -r requirements.txt
streamlit run app.py
