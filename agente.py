"""
M6 - Agente com ferramenta (vs RAG simples).

Decisao do agente:
    1. Extrai da pergunta (via LLM) os campos estacao, dia e horario.
    2. Se os TRES vierem preenchidos -> e pergunta de numero exato: chama a
       ferramenta consultar_lotacao (determinista) e responde com o valor do CSV.
    3. Caso contrario -> cai no RAG simples (pico / melhor horario por estacao+dia).

E isso que da vantagem ao agente sobre o RAG semantico: numero exato por faixa,
onde o RAG so tem o resumo.

Teste: python agente.py
"""
import json
import re
import unicodedata

import ollama

from rag import responder as responder_rag, GEN_MODEL, RESPOSTA_RECUSA
from ferramentas import consultar_lotacao

NOTA = "Obs.: o horario e estimado por um perfil (picos as 07:00 e 18:00)."

# so usa a ferramenta quando a pergunta cita um horario explicito (ex.: "18:00", "7h")
TEM_HORARIO = re.compile(r"\b\d{1,2}[:h]\d{0,2}\b")


def _slug(texto: str) -> str:
    t = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    return "".join(c if c.isalnum() else "-" for c in t.lower()).strip("-")


def _extrair_slots(pergunta: str) -> dict:
    resp = ollama.chat(
        model=GEN_MODEL,
        format="json",
        options={"temperature": 0},
        messages=[
            {
                "role": "system",
                "content": (
                    "Extraia da pergunta sobre lotacao do metro: estacao (nome da estacao), "
                    "dia (segunda a domingo) e horario (formato HH:MM). Use null quando o "
                    "campo nao aparecer. Responda JSON com as chaves estacao, dia, horario."
                ),
            },
            {"role": "user", "content": pergunta},
        ],
    )
    try:
        return json.loads(resp["message"]["content"])
    except (json.JSONDecodeError, KeyError):
        return {}


def responder_agente(pergunta: str) -> dict:
    # so tenta a ferramenta quando ha um horario explicito no texto da pergunta
    slots = _extrair_slots(pergunta) if TEM_HORARIO.search(pergunta) else {}
    estacao, dia, horario = slots.get("estacao"), slots.get("dia"), slots.get("horario")

    # caminho da ferramenta: pergunta de numero exato
    if estacao and dia and horario:
        r = consultar_lotacao(estacao, dia, horario)
        if r.get("encontrado"):
            resposta = (
                f"Em {r['estacao']} (Linha {r['linha']}), {r['dia']} as {r['faixa']}: "
                f"{r['entradas_previstas']} entradas previstas, categoria {r['categoria']} "
                f"(indice {r['indice_lotacao']}). {NOTA}"
            )
            return {
                "pergunta": pergunta,
                "resposta": resposta,
                "fonte": f"lot-{_slug(r['estacao'])}-{_slug(r['dia'])}-l{str(r['linha']).split('-')[0].strip()}",
                "confianca": 1.0,
                "status": "ok",
                "ferramenta": "consultar_lotacao",
            }
        return {
            "pergunta": pergunta,
            "resposta": RESPOSTA_RECUSA,
            "fonte": None,
            "confianca": 0.0,
            "status": "nao_consta",
            "ferramenta": "consultar_lotacao",
        }

    # caminho RAG: pico / melhor horario / categoria
    out = responder_rag(pergunta)
    out["ferramenta"] = None
    return out


if __name__ == "__main__":
    exemplos = [
        "Quantas pessoas entram em Corinthians-Itaquera na terca as 7h?",  # ferramenta
        "Qual o melhor horario para entrar na Se na segunda?",             # RAG
        "Qual a lotacao da estacao Paulista na terca as 8h?",              # fora -> recusa
    ]
    for p in exemplos:
        print(json.dumps(responder_agente(p), ensure_ascii=False, indent=2))
        print("-" * 60)