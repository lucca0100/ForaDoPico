"""
M10 - API do ForaDoPico (FastAPI).

Expoe o assistente de lotacao como endpoint HTTP. O app do CLT consome ESTE
contrato, sem conhecer o RAG/agente por dentro.

Rodar (da RAIZ, com Ollama aberto e base indexada):
    uvicorn api.main:app --reload
Docs: http://127.0.0.1:8000/docs

Contrato:
    POST /perguntar
    body:     { "pergunta": "Quantas pessoas entram na Se na segunda as 18h?" }
    resposta: { "pergunta": "...", "resposta": "...", "fontes": ["lot-se-segunda-l1"],
                "recusou": false, "confianca": 1.0 }
"""
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from agente import responder_agente

app = FastAPI(title="ForaDoPico - Assistente de Lotacao", version="2.0.0")

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)


class PerguntaIn(BaseModel):
    pergunta: str


class RespostaOut(BaseModel):
    pergunta: str
    resposta: str
    fontes: list[str]
    recusou: bool
    confianca: float


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/perguntar", response_model=RespostaOut)
def perguntar(entrada: PerguntaIn) -> RespostaOut:
    r = responder_agente(entrada.pergunta)
    fontes = [r["fonte"]] if r.get("fonte") else []
    return RespostaOut(
        pergunta=r["pergunta"],
        resposta=r["resposta"],
        fontes=fontes,
        recusou=(r["status"] == "nao_consta"),
        confianca=r["confianca"],
    )