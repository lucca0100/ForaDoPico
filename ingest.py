"""
Bloco 4 (parte 1) - Ingestao da base de conhecimento no ChromaDB.

Le base/base_conhecimento.json, gera o embedding de cada trecho com o modelo
bge-m3 (via Ollama) e grava tudo num indice vetorial persistente em ./chroma_db.

Pre-requisitos:
    - Ollama rodando (app aberto) com o modelo bge-m3 baixado
    - pip install -r requirements.txt

Rodar:
    python ingest.py
"""
import json
from pathlib import Path

import chromadb
import ollama

BASE_PATH = Path("base/base_conhecimento.json")
CHROMA_DIR = "chroma_db"
COLLECTION = "foradopico"
EMBED_MODEL = "bge-m3"


def carregar_base(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def gerar_embedding(texto: str) -> list[float]:
    resp = ollama.embeddings(model=EMBED_MODEL, prompt=texto)
    return resp["embedding"]


def main() -> None:
    trechos = carregar_base(BASE_PATH)
    print(f"Lidos {len(trechos)} trechos da base.")

    client = chromadb.PersistentClient(path=CHROMA_DIR)

    # recria a colecao do zero para nao duplicar trechos a cada execucao
    try:
        client.delete_collection(COLLECTION)
    except Exception:
        pass
    col = client.create_collection(
        name=COLLECTION, metadata={"hnsw:space": "cosine"}
    )

    ids, docs, metas, embs = [], [], [], []
    for t in trechos:
        ids.append(t["id"])
        docs.append(t["texto"])
        metas.append(
            {
                "categoria": t.get("categoria", ""),
                "fonte": t.get("fonte", ""),
                "atualizado_em": t.get("atualizado_em", ""),
            }
        )
        embs.append(gerar_embedding(t["texto"]))
        print(f"  embedding gerado: {t['id']}")

    col.add(ids=ids, documents=docs, metadatas=metas, embeddings=embs)
    print(f"\nIndexados {col.count()} trechos em ./{CHROMA_DIR} "
          f"(colecao '{COLLECTION}').")


if __name__ == "__main__":
    main()
