"""
M4/M8 - Gera o testset com gabarito tirado do proprio CSV.

Tres tipos de pergunta de escopo:
  A) pico          -> melhor respondida pelo RAG (resumo por estacao+dia)
  B) melhor horario-> idem
  C) numero exato  -> SO a ferramenta consultar_lotacao acerta (RAG nao tem a faixa)
Mais casos 'nao_consta' (fora de cobertura).

Cada pergunta tem 'valor_esperado' para a nota baseada no conteudo da resposta.
Saida: avaliacao/testset.json
"""
import json
import unicodedata
from pathlib import Path

import pandas as pd

CSV = "base/dados/vw_app_lotacao_prevista.csv"
SAIDA = Path("avaliacao/testset.json")

AMOSTRA = [
    ("Corinthians-Itaquera", "Terça"), ("República", "Segunda"), ("Brás", "Sexta"),
    ("Ana Rosa", "Quarta"), ("Tatuapé", "Quinta"), ("Belém", "Terça"),
    ("Artur Alvim", "Sábado"), ("Carandiru", "Segunda"),
]
FAIXA_EXATA = "18:00"  # perguntas de numero exato nesta faixa


def slug(texto: str) -> str:
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return "".join(c if c.isalnum() else "-" for c in t.lower()).strip("-")


def main() -> None:
    df = pd.read_csv(CSV, encoding="utf-8-sig")
    df.columns = [c.strip() for c in df.columns]

    testset, n = [], 1
    for estacao, dia in AMOSTRA:
        g = df[(df["estacao_nome"] == estacao) & (df["dia_semana_nome"] == dia)]
        if g.empty:
            continue
        num = str(g["linha_nome"].iloc[0]).split("-")[0].strip()
        fonte = f"lot-{slug(estacao)}-{slug(dia)}-l{num}"
        pico = g.loc[g["entradas_previstas"].idxmax()]
        melhor = g.loc[g["indice_lotacao"].idxmin()]

        testset.append({
            "id": f"q{n:03d}", "tipo": "pico",
            "pergunta": f"Qual o horario de pico em {estacao} na {dia}?",
            "status_esperado": "ok", "fonte_esperada": fonte,
            "valor_esperado": pico["faixa"],
            "resposta_esperada": f"Pico as {pico['faixa']} ({pico['categoria']}).",
        }); n += 1
        testset.append({
            "id": f"q{n:03d}", "tipo": "melhor_horario",
            "pergunta": f"Qual o melhor horario para entrar em {estacao} na {dia}?",
            "status_esperado": "ok", "fonte_esperada": fonte,
            "valor_esperado": melhor["faixa"],
            "resposta_esperada": f"Melhor entrada as {melhor['faixa']} ({melhor['categoria']}).",
        }); n += 1

        # C) numero exato na faixa fixa (so a ferramenta acerta)
        linha_faixa = g[g["faixa"] == FAIXA_EXATA]
        if not linha_faixa.empty:
            entradas = int(round(linha_faixa.iloc[0]["entradas_previstas"]))
            testset.append({
                "id": f"q{n:03d}", "tipo": "numero_exato",
                "pergunta": f"Quantas pessoas entram em {estacao} na {dia} as {FAIXA_EXATA}?",
                "status_esperado": "ok", "fonte_esperada": fonte,
                "valor_esperado": str(entradas),
                "resposta_esperada": f"{entradas} entradas previstas as {FAIXA_EXATA}.",
            }); n += 1

    fora = [
        "Qual a lotacao da estacao Paulista na Linha 4-Amarela?",
        "Como esta a lotacao na CPTM Linha 9-Esmeralda?",
        "Qual era o horario de pico da Se em 2025?",
        "Qual a estacao mais bonita do metro?",
        "Como esta o metro de Campinas hoje?",
    ]
    for p in fora:
        testset.append({
            "id": f"q{n:03d}", "tipo": "fora_de_escopo", "pergunta": p,
            "status_esperado": "nao_consta", "fonte_esperada": None,
            "valor_esperado": None,
            "resposta_esperada": "Nao consta (fora da cobertura: Linhas 1 e 3, jan-set/2026).",
        }); n += 1

    SAIDA.write_text(json.dumps(testset, ensure_ascii=False, indent=2), encoding="utf-8")
    ok = sum(1 for q in testset if q["status_esperado"] == "ok")
    nao = sum(1 for q in testset if q["status_esperado"] == "nao_consta")
    exato = sum(1 for q in testset if q.get("tipo") == "numero_exato")
    print(f"Gerado {SAIDA}: {len(testset)} perguntas ({ok} ok, {nao} nao_consta, {exato} numero_exato).")


if __name__ == "__main__":
    main()