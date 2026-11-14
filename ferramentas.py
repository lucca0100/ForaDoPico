"""
M5 - Ferramenta do agente: consultar_lotacao(estacao, dia, horario).

Le a view vw_app_lotacao_prevista e devolve o numero EXATO de entradas previstas,
o indice e a categoria para uma estacao / dia / faixa de 15 min. E deterministica -
e o que da ao agente a vantagem sobre o RAG semantico em perguntas de numero exato.

Teste: python ferramentas.py
"""
import unicodedata

import pandas as pd

CSV = "base/dados/vw_app_lotacao_prevista.csv"

_df = pd.read_csv(CSV, encoding="utf-8-sig")
_df.columns = [c.strip() for c in _df.columns]

DIAS = {
    "segunda": "Segunda", "terca": "Terça", "quarta": "Quarta", "quinta": "Quinta",
    "sexta": "Sexta", "sabado": "Sábado", "domingo": "Domingo",
}


def _norm(texto: str) -> str:
    t = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    return t.strip().lower()


_df["_estacao_norm"] = _df["estacao_nome"].map(_norm)


def _faixa_proxima(horario: str) -> str:
    """Arredonda 'HH:MM' para a faixa de 15 min disponivel mais proxima."""
    try:
        h, m = map(int, horario.strip().split(":"))
    except ValueError:
        return horario
    total = h * 60 + m
    faixas = sorted(_df["faixa"].unique(),
                    key=lambda f: int(f[:2]) * 60 + int(f[3:]))
    melhor = min(faixas, key=lambda f: abs(int(f[:2]) * 60 + int(f[3:]) - total))
    return melhor


def consultar_lotacao(estacao: str, dia: str, horario: str) -> dict:
    """Retorna a lotacao prevista para estacao/dia/faixa, ou encontrado=False."""
    est = _norm(estacao)
    dia_fmt = DIAS.get(_norm(dia), dia)
    faixa = _faixa_proxima(horario)

    sub = _df[(_df["_estacao_norm"].str.contains(est, na=False)) &
              (_df["dia_semana_nome"] == dia_fmt) &
              (_df["faixa"] == faixa)]
    if sub.empty:
        return {"encontrado": False, "estacao": estacao, "dia": dia_fmt, "faixa": faixa}

    r = sub.iloc[0]
    return {
        "encontrado": True,
        "estacao": r["estacao_nome"],
        "linha": r["linha_nome"],
        "dia": dia_fmt,
        "faixa": faixa,
        "entradas_previstas": int(round(r["entradas_previstas"])),
        "indice_lotacao": round(float(r["indice_lotacao"]), 3),
        "categoria": r["categoria"],
    }


if __name__ == "__main__":
    for args in [("Corinthians-Itaquera", "terca", "07:00"),
                 ("Se", "segunda", "18:10"),
                 ("Paulista", "segunda", "08:00")]:  # Paulista nao existe -> encontrado False
        print(args, "->", consultar_lotacao(*args))
