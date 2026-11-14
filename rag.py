"""
Bloco 5 - Geracao fundamentada (RAG) com saida em JSON e recusa 'nao_consta'.

Fluxo:
    1. Gera o embedding da pergunta (bge-m3) e busca os trechos mais proximos no Chroma.
    2. Se a similaridade do melhor trecho for menor que LIMIAR -> 'nao_consta' (recusa rapida).
    3. Caso contrario, o llama3.1 recebe SO os trechos recuperados e responde em JSON,
       podendo ainda recusar se os trechos nao sustentarem a resposta
       (ex.: pergunta sobre outra cidade). Essa e a 2a camada de recusa.

Contrato de saida (o mesmo que a API devolve no Bloco 9):
    {
      "pergunta": str,
      "resposta": str,
      "fonte": str | None,      # id do trecho usado
      "confianca": float,       # similaridade do melhor trecho (0..1)
      "status": "ok" | "nao_consta"
    }

Pre-requisitos: ter rodado 'python ingest.py' e estar com o Ollama aberto.
Teste rapido:  python rag.py
"""
import json

import chromadb
import ollama

CHROMA_DIR = "chroma_db"
COLLECTION = "foradopico"
EMBED_MODEL = "bge-m3"
GEN_MODEL = "llama3.1:8b"
LIMIAR = 0.56          # definido no Bloco 4 pelo intervalo observado
TOP_K = 3

RESPOSTA_RECUSA = ("Nao consta na base. Este assistente cobre apenas a lotacao das "
                   "Linhas 1-Azul e 3-Vermelha do Metro-SP, de janeiro a setembro de 2026.")

SYSTEM_PROMPT = (
    "Voce e o assistente ForaDoPico. Responde SOMENTE sobre LOTACAO e MELHOR HORARIO "
    "das Linhas 1-Azul e 3-Vermelha do Metro de Sao Paulo (periodo jan-set/2026), "
    "usando EXCLUSIVAMENTE os trechos fornecidos.\n"
    "Regras:\n"
    "- Use apenas a informacao dos TRECHOS. Nunca invente nem use conhecimento proprio.\n"
    "- Se os trechos nao contem a resposta, ou a pergunta e sobre outra linha (2, 4...), "
    "CPTM, outro ano, ou pede opiniao, use status 'nao_consta'.\n"
    "- Quando a resposta envolver horario ou numero, lembre que a estimativa por faixa "
    "vem de um perfil (picos as 07:00 e 18:00) e mencione isso brevemente.\n"
    "- Responda em JSON valido com as chaves: resposta (string), fonte (id do trecho "
    "usado, ou null), status ('ok' ou 'nao_consta').\n"
    "- 'fonte' deve ser o id do trecho que sustenta a resposta."
)

_client = chromadb.PersistentClient(path=CHROMA_DIR)
_col = _client.get_collection(COLLECTION)


def _embed(texto: str) -> list[float]:
    return ollama.embeddings(model=EMBED_MODEL, prompt=texto)["embedding"]


def buscar(pergunta: str, k: int = TOP_K) -> list[dict]:
    res = _col.query(
        query_embeddings=[_embed(pergunta)],
        n_results=k,
        include=["documents", "metadatas", "distances"],
    )
    trechos = []
    for i, _id in enumerate(res["ids"][0]):
        trechos.append(
            {
                "id": _id,
                "texto": res["documents"][0][i],
                "fonte": res["metadatas"][0][i].get("fonte", ""),
                "similaridade": 1 - res["distances"][0][i],
            }
        )
    return trechos


def _gerar(pergunta: str, trechos: list[dict]) -> dict:
    contexto = "\n\n".join(f"[{t['id']}] {t['texto']}" for t in trechos)
    user = f"TRECHOS:\n{contexto}\n\nPERGUNTA: {pergunta}"
    resp = ollama.chat(
        model=GEN_MODEL,
        format="json",
        options={"temperature": 0},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user},
        ],
    )
    try:
        return json.loads(resp["message"]["content"])
    except (json.JSONDecodeError, KeyError):
        return {"resposta": RESPOSTA_RECUSA, "fonte": None, "status": "nao_consta"}


def responder(pergunta: str) -> dict:
    trechos = buscar(pergunta)
    sim_top1 = trechos[0]["similaridade"] if trechos else 0.0

    # 1a camada: recusa por baixa similaridade
    if sim_top1 < LIMIAR:
        return {
            "pergunta": pergunta,
            "resposta": RESPOSTA_RECUSA,
            "fonte": None,
            "confianca": round(sim_top1, 3),
            "status": "nao_consta",
        }

    # 2a camada: geracao fundamentada (pode recusar mesmo com similaridade alta)
    bruto = _gerar(pergunta, trechos)
    status = bruto.get("status", "nao_consta")
    if status != "ok":
        return {
            "pergunta": pergunta,
            "resposta": RESPOSTA_RECUSA,
            "fonte": None,
            "confianca": round(sim_top1, 3),
            "status": "nao_consta",
        }
    return {
        "pergunta": pergunta,
        "resposta": bruto.get("resposta", ""),
        "fonte": bruto.get("fonte"),
        "confianca": round(sim_top1, 3),
        "status": "ok",
    }


if __name__ == "__main__":
    exemplos = [
        "Qual o horario de pico na Se na segunda?",
        "Qual o melhor horario para entrar em Itaquera na terca?",
        "Qual a lotacao na Linha 4-Amarela?",        # deve recusar
        "Qual a estacao mais bonita do metro?",      # deve recusar
    ]
    for p in exemplos:
        print(json.dumps(responder(p), ensure_ascii=False, indent=2))
        print("-" * 60)