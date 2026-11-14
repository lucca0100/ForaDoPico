"""
Bloco 4 (parte 2) - Avaliacao da busca: recall@1, recall@3 e justificativa do limiar.

Para cada pergunta de escopo (status "ok") do testset, verifica se o trecho
esperado (fonte_esperada) aparece no top-1 e no top-3 da busca vetorial.
Para as perguntas fora de escopo ("nao_consta"), mede a similaridade do top-1 -
ela deve ficar BAIXA, o que justifica o limiar de recusa.

Pre-requisitos:
    - ter rodado antes:  python ingest.py
    - Ollama rodando com bge-m3

Rodar (a partir da raiz do projeto):
    python avaliacao/avaliar_retrieval.py
"""
import json
from pathlib import Path

import chromadb
import ollama

CHROMA_DIR = "chroma_db"
COLLECTION = "foradopico"
EMBED_MODEL = "bge-m3"
TESTSET = Path("avaliacao/testset.json")


def embed(texto: str) -> list[float]:
    return ollama.embeddings(model=EMBED_MODEL, prompt=texto)["embedding"]


def main() -> None:
    testset = json.loads(TESTSET.read_text(encoding="utf-8"))
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    col = client.get_collection(COLLECTION)

    perguntas_ok = [q for q in testset if q["status_esperado"] == "ok"]
    perguntas_nao = [q for q in testset if q["status_esperado"] == "nao_consta"]

    acertos1 = acertos3 = 0
    sims_ok, sims_nao = [], []

    print("=== Perguntas de escopo (ok) ===")
    for q in perguntas_ok:
        res = col.query(
            query_embeddings=[embed(q["pergunta"])],
            n_results=3,
            include=["distances", "metadatas"],
        )
        ids = res["ids"][0]
        dists = res["distances"][0]
        sim_top1 = 1 - dists[0]              # cosine_sim = 1 - cosine_distance
        sims_ok.append(sim_top1)

        esperado = q["fonte_esperada"]
        top1_ok = ids[0] == esperado
        top3_ok = esperado in ids[:3]
        acertos1 += int(top1_ok)
        acertos3 += int(top3_ok)
        print(f"[{q['id']}] top1={ids[0]:<22} sim={sim_top1:.3f} "
              f"| @1 {'OK' if top1_ok else ' X'} | @3 {'OK' if top3_ok else ' X'}")

    print("\n=== Perguntas fora de escopo (sim_top1 deve ser baixa) ===")
    for q in perguntas_nao:
        res = col.query(
            query_embeddings=[embed(q["pergunta"])],
            n_results=1,
            include=["distances"],
        )
        sim_top1 = 1 - res["distances"][0][0]
        sims_nao.append(sim_top1)
        print(f"[{q['id']}] sim_top1={sim_top1:.3f}")

    n = len(perguntas_ok)
    print("\n=== Resultado ===")
    print(f"recall@1 = {acertos1}/{n} = {acertos1 / n:.1%}")
    print(f"recall@3 = {acertos3}/{n} = {acertos3 / n:.1%}")

    if sims_ok and sims_nao:
        print(f"\nSimilaridade top-1  (ok) : min={min(sims_ok):.3f}  "
              f"media={sum(sims_ok)/len(sims_ok):.3f}")
        print(f"Similaridade top-1 (nao) : max={max(sims_nao):.3f}  "
              f"media={sum(sims_nao)/len(sims_nao):.3f}")
        limiar = (min(sims_ok) + max(sims_nao)) / 2
        print(f"\nLimiar sugerido (meio do intervalo) = {limiar:.3f}")
        print("Acima do limiar -> responde com fonte; abaixo -> 'nao_consta'.")


if __name__ == "__main__":
    main()
