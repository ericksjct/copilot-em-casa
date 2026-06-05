# PROJECT: [nome]

Hub de contexto durável do projeto. Cresce por acréscimo: o miolo (Objetivo,
Stack, Convenções) muda raramente; Roadmap e Decisões ganham linha nova conforme
o projeto anda. Cole no início da thread junto com `RULES.md` e `STATE.md`.

Gerado e atualizado pela persona Bootstrapper (Objetivo, Stack, Convenções,
Roadmap) e pelo Productionizer (seção Decisões, via bloco UPDATE).

## Objetivo

[1-2 parágrafos: o que esse projeto resolve e pra quem]

## Stack

- Linguagem/versão: [Python 3.x, etc.]
- Libs principais: [pandas, polars, duckdb, etc.]
- Runtime/deploy: [local, docker, airflow, etc.]
- Output: [parquet, sqlserver, powerbi, etc.]

## Estrutura de alto nível

[árvore de 2 níveis, conceitual]

## Convenções deste projeto

- Naming: [padrão do projeto]
- Logging: [stdlib JSON, structlog, etc.]
- Configuração: [.env, config.yaml, etc.]
- Testes: [pytest, smoke manual, etc.]

## Roadmap

Fases em ordem. Status: `[pendente]` | `[em andamento]` | `[concluída]` | `[descartada]`.

### Fase 1: [nome] [pendente]

- Objetivo: [1 frase]
- Pronto quando: [critério verificável]
- Plano: [`docs/copiloto/planos/fase-1-nome.md` quando existir, senão "a planejar"]

### Fase 2: [nome] [pendente]

- Objetivo: [1 frase]
- Pronto quando: [critério verificável]
- Plano: [a planejar]

## Decisões

Log compacto. Uma entrada por decisão durável — a que vale além de uma fase, troca
ou introduz dependência, ou fixa convenção que outras fases seguem. Provada no
protótipo, não suposta. A numeração sai da linha "Próximos números" no `STATE.md`.
Quem escreve aqui é o Productionizer (via bloco UPDATE).

- D-001 ([YYYY-MM] · fase N): [decisão em 1-2 linhas]. Descartado: [alternativa refutada]. Consequência: [impacto no design ou nos passos].

## Fora de escopo

- [o que esse projeto NÃO faz]
