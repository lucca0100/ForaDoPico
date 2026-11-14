# Analise de erros reais — ForaDoPico (item 07)

Cinco erros observados durante a construcao e avaliacao do assistente de lotacao,
todos tirados de execucoes reais (ingest, rag, agente e comparar_configs).

## Erro 1 — IDs duplicados na estacao Se (Linha 1 x Linha 3)
- **Sintoma:** o `ingest.py` abortou com `DuplicateIDError` e o indice ficou vazio (count = 0); todas as respostas viravam `nao_consta` com confianca 0.
- **Causa:** a Se e estacao de transferencia e aparece nas Linhas 1-Azul e 3-Vermelha; os dois trechos geravam o mesmo id (`lot-se-<dia>`).
- **Correcao:** incluir a linha no id (`lot-se-segunda-l1` x `lot-se-segunda-l3`). Resolveu: 289 ids unicos.

## Erro 2 — Agente roteando mal perguntas de pico/melhor horario
- **Sintoma:** no primeiro placar, o agente teve acuracia (69%) ABAIXO do RAG (72%).
- **Causa:** o extrator de campos inventava um horario em perguntas que nao tinham (pico/melhor), mandando-as para a ferramenta por engano e errando a resposta.
- **Correcao:** so acionar a ferramenta quando ha horario explicito no texto (regex `\d{1,2}[:h]\d{0,2}`). A acuracia do agente subiu para 97%.

## Erro 3 — RAG simples zera nas perguntas de numero exato
- **Sintoma:** `num_exato` = 0% no RAG simples.
- **Causa:** o trecho da base e um resumo (pico e melhor horario); nao contem o numero de cada faixa de 15 min. O RAG semantico nao tem de onde tirar o valor exato.
- **Correcao:** a ferramenta `consultar_lotacao` le o CSV e devolve o numero exato — o agente chega a 88% nessa coluna.

## Erro 4 — "Melhor horario" caindo de madrugada
- **Sintoma:** o melhor horario para entrar aparece as 22:15 / 23:15 (menor lotacao real, porem inutil para quem vai trabalhar).
- **Causa:** o calculo usa o menor indice de lotacao do dia inteiro, sem janela de deslocamento.
- **Correcao:** restringir o "melhor horario" a uma janela util (ex.: 06:00-20:00) na geracao da base.

## Erro 5 — Baseline sem contexto alucina
- **Sintoma:** a configuracao `sem_contexto` recusou so 40% das perguntas fora de escopo e teve acuracia de 7%.
- **Causa:** sem base e sem mecanismo de recusa, o modelo tenta responder tudo, inclusive outras linhas, CPTM e outros anos.
- **Correcao:** e o motivo do RAG + ferramenta; a comparacao mostra o ganho de 7% para 72% (RAG) e 97% (agente).