"""
M2 - Constroi a base de conhecimento a partir do CSV vw_app_lotacao_prevista.

Para cada estacao + dia da semana, gera UM trecho-resumo com o pico e o melhor
horario de entrada. Acrescenta trechos de metodologia e de regras da escala.
A fonte de cada trecho e a view da camada Ouro.

Uso:
    python construir_base.py base/dados/vw_app_lotacao_prevista.csv

Saida: base/base_conhecimento.json
"""
import json
import sys
import unicodedata
from pathlib import Path

import pandas as pd

FONTE = "vw_app_lotacao_prevista - Ouro ForaDoPico - dados do Metro jan-set/2026"
SAIDA = Path("base/base_conhecimento.json")

ORDEM_DIAS = ["Segunda", "Terca", "Quarta", "Quinta", "Sexta", "Sabado", "Domingo"]


def slug(texto: str) -> str:
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return "".join(c if c.isalnum() else "-" for c in t.lower()).strip("-")


def construir(csv_path: str) -> list[dict]:
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    df.columns = [c.strip() for c in df.columns]

    trechos = []
    chaves = df.groupby(["linha_nome", "estacao_nome", "dia_semana_iso",
                         "dia_semana_nome"], sort=False)

    for (linha, estacao, _dia_iso, dia_nome), g in chaves:
        pico = g.loc[g["entradas_previstas"].idxmax()]
        melhor = g.loc[g["indice_lotacao"].idxmin()]
        texto = (
            f"{estacao} (Linha {linha}), {dia_nome}: "
            f"pico as {pico['faixa']} ({pico['categoria']}, "
            f"{int(round(pico['entradas_previstas']))} entradas previstas); "
            f"melhor horario para entrar as {melhor['faixa']} ({melhor['categoria']})."
        )
        num = str(linha).split("-")[0].strip()  # "1-Azul" -> "1"
        trechos.append(
            {
                "id": f"lot-{slug(estacao)}-{slug(dia_nome)}-l{num}",
                "categoria": "lotacao",
                "linha": linha,
                "estacao": estacao,
                "dia": dia_nome,
                "texto": texto,
                "fonte": FONTE,
                "licenca": "dado agregado por estacao, sem dado pessoal (LGPD ok)",
                "atualizado_em": "2026-11-13",
            }
        )

    # trechos de apoio
    trechos.append(
        {
            "id": "metodologia-001",
            "categoria": "metodologia",
            "texto": (
                "A lotacao por faixa de 15 minutos e ESTIMADA. O Metro publica apenas o "
                "total diario de entradas por estacao (jan a set/2026); a distribuicao por "
                "horario vem de um perfil tipico, com picos as 07:00 e as 18:00. Portanto os "
                "numeros por faixa sao uma estimativa, nao uma medicao hora a hora."
            ),
            "fonte": FONTE,
            "licenca": "metodologia documentada",
            "atualizado_em": "2026-11-13",
        }
    )
    trechos.append(
        {
            "id": "cobertura-001",
            "categoria": "cobertura",
            "texto": (
                "A base cobre apenas as Linhas 1-Azul e 3-Vermelha do Metro de Sao Paulo, "
                "no periodo de janeiro a setembro de 2026. Perguntas sobre outras linhas "
                "(2-Verde, 4-Amarela etc.), sobre a CPTM, ou sobre outros anos nao sao cobertas."
            ),
            "fonte": FONTE,
            "licenca": "escopo documentado",
            "atualizado_em": "2026-11-13",
        }
    )
    return trechos


def main() -> None:
    csv_path = sys.argv[1] if len(sys.argv) > 1 else "base/dados/vw_app_lotacao_prevista.csv"
    trechos = construir(csv_path)
    SAIDA.write_text(json.dumps(trechos, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Gerados {len(trechos)} trechos em {SAIDA}.")


if __name__ == "__main__":
    main()