# API do ForaDoPico (Bloco 9 / M10)

Expoe o assistente de lotacao como endpoint HTTP. O app do CLT consome este contrato.

## Rodar
A partir da **raiz**, com o Ollama aberto e a base indexada (`python ingest.py`):

```bash
uvicorn api.main:app --reload
```

- Swagger: http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/health

## Contrato

**POST** `/perguntar`

Request:
```json
{ "pergunta": "Quantas pessoas entram na Se na segunda as 18h?" }
```

Response:
```json
{
  "pergunta": "Quantas pessoas entram na Se na segunda as 18h?",
  "resposta": "Em Se (Linha 1-Azul), Segunda as 18:00: ... entradas previstas, categoria ...",
  "fontes": ["lot-se-segunda-l1"],
  "recusou": false,
  "confianca": 1.0
}
```

Fora da cobertura (outra linha, CPTM, outro ano, opiniao): `recusou` vem `true`,
`fontes` vem `[]` e `resposta` traz a mensagem de recusa.