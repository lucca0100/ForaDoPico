"""
M8 - Placar das 3 configuracoes (item 06), nota baseada no VALOR da resposta.

Configuracoes:
    A) sem_contexto - LLM sozinho, sem base
    B) rag_simples  - rag.responder
    C) agente       - agente.responder_agente (usa a ferramenta consultar_lotacao)

Metricas:
    - resposta_correta : % das perguntas de escopo com status ok E o valor esperado na resposta
    - exato_correto    : idem, so nas perguntas de numero exato (onde o agente ganha do RAG)
    - recusa_correta   : % das fora de escopo que viraram 'nao_consta'
    - acuracia         : (escopo correto + recusa correta) / total

Gera: placar impresso, avaliacao/placar.json e avaliacao/placar.png
ATENCAO: dezenas de chamadas ao LLM em CPU - pode levar varios minutos.
Rodar: python avaliacao/comparar_configs.py
"""
import json
from pathlib import Path

import matplotlib.pyplot as plt
import ollama

from rag import responder as responder_rag, GEN_MODEL
from agente import responder_agente

TESTSET = Path("avaliacao/testset.json")
OUT_JSON = Path("avaliacao/placar.json")
OUT_PNG = Path("avaliacao/placar.png")


def sem_contexto(pergunta: str) -> dict:
    resp = ollama.chat(
        model=GEN_MODEL, format="json", options={"temperature": 0},
        messages=[
            {"role": "system", "content": (
                "Responda a duvida sobre lotacao do metro de SP. Responda em JSON com as "
                "chaves: resposta (string), fonte (null), status ('ok' ou 'nao_consta').")},
            {"role": "user", "content": pergunta},
        ],
    )
    try:
        d = json.loads(resp["message"]["content"])
    except (json.JSONDecodeError, KeyError):
        d = {"resposta": "", "status": "ok"}
    return {"status": d.get("status", "ok"), "resposta": d.get("resposta", "")}


def _ok_correto(q: dict, r: dict) -> bool:
    if r.get("status") != "ok":
        return False
    val = str(q.get("valor_esperado") or "").lower()
    return bool(val) and val in str(r.get("resposta", "")).lower()


def avaliar(nome: str, fn, ok_qs, nao_qs, exato_qs) -> dict:
    ok_corretos = sum(_ok_correto(q, fn(q["pergunta"])) for q in ok_qs)
    exato_corretos = sum(_ok_correto(q, fn(q["pergunta"])) for q in exato_qs)
    recusa_ok = sum(1 for q in nao_qs if fn(q["pergunta"]).get("status") == "nao_consta")
    n_ok, n_nao, n_ex = len(ok_qs), len(nao_qs), len(exato_qs)
    return {
        "config": nome,
        "resposta_correta": ok_corretos / n_ok,
        "exato_correto": exato_corretos / n_ex if n_ex else 0.0,
        "recusa_correta": recusa_ok / n_nao,
        "acuracia": (ok_corretos + recusa_ok) / (n_ok + n_nao),
    }


def main() -> None:
    testset = json.loads(TESTSET.read_text(encoding="utf-8"))
    ok_qs = [q for q in testset if q["status_esperado"] == "ok"]
    nao_qs = [q for q in testset if q["status_esperado"] == "nao_consta"]
    exato_qs = [q for q in testset if q.get("tipo") == "numero_exato"]

    configs = [("sem_contexto", sem_contexto), ("rag_simples", responder_rag),
               ("agente", responder_agente)]

    resultados = []
    for nome, fn in configs:
        print(f"Avaliando: {nome} ...")
        resultados.append(avaliar(nome, fn, ok_qs, nao_qs, exato_qs))

    print("\n=== PLACAR ===")
    print(f"{'config':<14}{'resposta':>10}{'num_exato':>11}{'recusa':>9}{'acuracia':>10}")
    for r in resultados:
        print(f"{r['config']:<14}{r['resposta_correta']:>9.0%}{r['exato_correto']:>11.0%}"
              f"{r['recusa_correta']:>9.0%}{r['acuracia']:>10.0%}")

    OUT_JSON.write_text(json.dumps(resultados, ensure_ascii=False, indent=2), encoding="utf-8")

    labels = [r["config"] for r in resultados]
    metricas = ["resposta_correta", "exato_correto", "recusa_correta", "acuracia"]
    nomes = ["Resposta correta", "Numero exato", "Recusa correta", "Acuracia"]
    x = range(len(labels))
    w = 0.2
    fig, ax = plt.subplots(figsize=(9, 5))
    for i, m in enumerate(metricas):
        ax.bar([p + i * w for p in x], [r[m] * 100 for r in resultados], w, label=nomes[i])
    ax.set_ylabel("%")
    ax.set_title("Placar das 3 configuracoes - ForaDoPico (lotacao)")
    ax.set_xticks([p + 1.5 * w for p in x])
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 105)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=120)
    print(f"\nSalvos: {OUT_JSON} e {OUT_PNG}")


if __name__ == "__main__":
    main()