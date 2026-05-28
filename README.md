# Copilot em Casa

Um sistema para rodar um fluxo estruturado tipo **GSD** (Get Shit Done) dentro do
**Copilot do Windows** (GPT-4) — que não escreve em disco, não tem comandos slash, não
roda agentes e não guarda memória entre threads. Aqui **você é o runtime**: cola o
contexto, recebe artefatos cercados por marcadores HTML e salva os arquivos à mão.

Este repositório é o **toolkit portátil**: guarda o sistema (personas, regras, scripts,
templates), não o estado de um projeto específico. Para tocar um projeto de trabalho,
você instala o toolkit nele (ver [Instalar num projeto](#instalar-num-projeto-de-trabalho)).

## Mapa do repositório

```text
copilot-em-casa/
├── README.md                   este guia
├── personas/                   as 6 personas do fluxo (uma por papel)
├── scripts/gsd/                gerador do snapshot do código (árvore + assinaturas + schemas)
└── templates/                  tudo que você copia pro projeto de trabalho
    ├── RULES.md                regras de formatação/comportamento — colar no início de toda thread
    ├── manual-copilot-windows.md   referência completa: o porquê de cada regra (parser, anti-drift)
    └── docs/gsd/
        ├── STATE.md            estado vivo (muda a cada turno)
        ├── context/            PROJECT.md, ROADMAP.md, CODEBASE-MAP.md
        ├── adr/                decisões de arquitetura
        ├── plans/              planos por fase
        └── handovers/          relatórios (ex: Prototyper)
```

## Os três tipos de contexto

Entender essa separação é o que evita "se perder":

- **Regras (`templates/RULES.md`)** — fixas. Valem para todo projeto e nunca mudam.
  Você cola no início de cada thread nova.
- **Templates (`templates/`)** — tudo que você copia pro repo de trabalho: as regras, o
  manual e os moldes do `docs/gsd/`. Os moldes ficam em branco; você preenche **lá**.
- **Estado vivo (`STATE.md` no projeto)** — muda a cada turno. É o único arquivo que você
  atualiza com frequência; por isso é curto.

Atenção: antes existia um único "STATE.md" que misturava regras (fixas) com estado
(volátil). Agora são coisas separadas — `RULES.md` é a lei, `STATE.md` é o diário.

## As personas

Cada persona é um papel com escopo travado. Cole o arquivo da persona no início da thread,
junto com `RULES.md` e o `STATE.md` do projeto.

| Persona | Use quando | Produz |
| --- | --- | --- |
| Bootstrapper | Início de projeto, ou registrar um ADR / nova fase | `PROJECT.md`, `ROADMAP.md` |
| Mapper | Precisa do mapa do código atualizado | `CODEBASE-MAP.md` |
| Architect | Há uma decisão de design / fase nova | HANDOFF, ADR, diagrama Mermaid |
| Prototyper | O design tem risco de não fechar — validar em dados reais | Relatório de validação (Jupyter) |
| Planner | Design fechado, decompor em passos executáveis | `PLAN.md` + um HANDOFF por passo |
| Implementer | Executar **um** passo do plano | Código do arquivo |

## O fluxo ponta a ponta

```text
[projeto novo]
   └─ Bootstrapper ........... cria PROJECT.md + ROADMAP.md
[código já existe]
   └─ python -m scripts.gsd → Mapper ... gera CODEBASE-MAP.md

[nova fase]
   └─ Architect .............. design → HANDOFF (+ ADR se durável)
        ├─ (design arriscado?) → Prototyper .. valida em Jupyter → relatório volta pro Architect
        └─ Planner ........... HANDOFF → PLAN.md + HANDOFFs por passo
             └─ Implementer ... executa passo 1, 2, ... N → código

STATE.md atravessa tudo: Architect, Prototyper, Planner e Implementer devolvem
um bloco "UPDATE STATE.md" ao final — você aplica no STATE.md do projeto.
```

Quem mexe em cada artefato:

- `PROJECT.md`, `ROADMAP.md` — só o **Bootstrapper**.
- `CODEBASE-MAP.md` — só o **Mapper**.
- `STATE.md` — você, aplicando os blocos UPDATE de Architect / Prototyper / Planner / Implementer.
- `adr/`, `plans/`, `handovers/` — Architect, Planner e Prototyper geram; você salva.

As personas trocam **handoffs** entre si (Architect→Planner, Planner→Implementer) e
emitem **INPUT BOOTSTRAPPER** quando algo precisa entrar no PROJECT/ROADMAP. Os números
de ADR e de fase são seus para atribuir.

## Como montar um prompt

No primeiro turno de uma thread, cole nesta ordem:

1. `RULES.md` (as regras fixas)
2. A persona do papel atual (ex: `personas/planner.md`)
3. O `STATE.md` do projeto + os arquivos de contexto que a persona pede (ver quadro abaixo)
4. Seu pedido

O que entra no item 3, por persona:

| Persona | Cole junto (além de RULES + STATE) |
| --- | --- |
| Bootstrapper | Descrição do projeto (modo "novo projeto"), ou PROJECT/ROADMAP atual + o delta / bloco INPUT BOOTSTRAPPER (demais modos) |
| Mapper | `.temp/codebase-snapshot.txt` (de `python -m scripts.gsd`); opcional: CODEBASE-MAP anterior |
| Architect | `CODEBASE-MAP.md` + os arquivos específicos do problema |
| Prototyper | HANDOFF do Architect (ou ADR) + caminho/amostra dos dados reais + a pergunta a validar |
| Planner | HANDOFF do Architect + os arquivos que ele listou em "Referências" |
| Implementer | O HANDOFF do passo + os arquivos colados com `=== ARQUIVO: path ===` |

Em cada turno seguinte, cole no **final** do pedido o sufixo dinâmico (está no fim do
`RULES.md`): ele reforça os marcadores de artefato, que são a primeira regra que o modelo
esquece em threads longas.

Ao receber a resposta, extraia cada artefato copiando o conteúdo **entre**
`<!-- INICIO: path -->` e `<!-- FIM: path -->` e salvando no `path` indicado pelo próprio
marcador. Se o destino é `.md` e o conteúdo não começa com `#`, adicione um H1 no topo
(regra MD041 — detalhe na seção 2.4.1 do manual).

## Instalar num projeto de trabalho

1. Copie o conteúdo de `templates/` para a raiz do repo de trabalho: vira `docs/gsd/`, mais `RULES.md` e `manual-copilot-windows.md` à mão para colar/consultar.
2. Copie `scripts/gsd/` para a raiz do repo de trabalho (precisa ser importável como `scripts.gsd`).
3. Garanta que `.temp/` está no `.gitignore` do projeto (o snapshot pode conter dados reais).
4. Preencha `PROJECT.md` e `ROADMAP.md` à mão, ou rode o Bootstrapper (modo "novo projeto").
5. Rode `python -m scripts.gsd` e passe o resultado pro Mapper para gerar o `CODEBASE-MAP.md`.

## Os scripts (`scripts/gsd/`)

Geram um snapshot do código para alimentar o Mapper e o Architect. Duas portas de uso:

Porta estática (sem o pipeline rodando) — gera árvore + assinaturas; schemas saem vazios:

```bash
python -m scripts.gsd
```

Porta runtime (dentro do `main.py` do pipeline) — registra DataFrames para popular a seção
de schemas:

```python
from scripts.gsd import registry, snapshot_completo

registry.add("balancete", df_balancete)
registry.add("cop", df_cop)
# ... no fim do pipeline ...
snapshot_completo()
```

Saída: `.temp/codebase-snapshot.txt` (três seções: ÁRVORE, ASSINATURAS, SCHEMAS).

Há ainda `snapshot_architect()`, que gera `.temp/architect-snapshot.txt` com **amostras
reais** dos DataFrames (3 linhas cada). **Esse arquivo pode conter PII / valores
financeiros — mantenha local, não cole em chat externo e não comite.**

## Referência

O `templates/manual-copilot-windows.md` documenta o porquê de cada regra: anti-aninhamento de
backtick, marcadores HTML, trava de escopo por SAÍDAS, as duas camadas de contexto e a
tabela completa de sintoma → decisão de design. Leia quando uma regra parecer arbitrária.
