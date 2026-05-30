# Copilot em Casa

Um sistema para rodar um fluxo estruturado tipo **GSD** (Get Shit Done) dentro do
**Copilot do Windows** (GPT-4) — que não escreve em disco, não tem comandos slash, não
roda agentes e não guarda memória entre threads. Aqui **você é o runtime**: cola o
contexto, recebe artefatos cercados por marcadores HTML e salva os arquivos à mão.

O núcleo do fluxo é **prototype-first**: você valida a ideia no Jupyter até ela fechar,
e só então transpila pra produção de forma estruturada — com gabaritos que provam que a
transpilação preservou o que o protótipo provou.

Este repositório é o **toolkit portátil**: guarda o sistema (personas, regras, scripts,
templates), não o estado de um projeto específico. Para tocar um projeto de trabalho,
você instala o toolkit nele (ver [Instalar num projeto](#instalar-num-projeto-de-trabalho)).

## Mapa do repositório

```text
copilot-em-casa/
├── README.md                   este guia
├── personas/                   as 5 personas do fluxo (uma por papel)
├── scripts/gsd/                snapshot do código + empacotador de contexto (pack)
└── templates/                  tudo que você copia pro projeto de trabalho
    ├── RULES.md                regras de formatação/comportamento — colar no início de toda thread
    ├── manual-copilot-windows.md   referência completa: o porquê de cada regra
    └── docs/gsd/
        ├── STATE.md            estado vivo (muda a cada turno)
        ├── context/            PROJECT.md (hub) e CODEBASE-MAP.md
        ├── plans/              planos por fase
        └── handovers/          relatório de validação do Prototyper
```

## Os tipos de contexto

Entender essa separação é o que evita "se perder":

- **Regras (`RULES.md`)** — fixas. Valem para todo projeto e nunca mudam. Cola no início
  de cada thread nova.
- **Contexto durável (`PROJECT.md`, `CODEBASE-MAP.md`)** — muda devagar e por acréscimo. O
  `PROJECT.md` é o **hub**: objetivo, stack, convenções, o Roadmap e as Decisões, tudo num
  arquivo só. O `CODEBASE-MAP.md` é gerado a partir do código.
- **Estado vivo (`STATE.md`)** — volátil, muda a cada turno. É curto de propósito.

Por isso o que você cola no início da thread cabe, na maioria dos turnos, em **dois
arquivos**: `PROJECT.md` + `STATE.md` (o `CODEBASE-MAP.md` só entra quando vai produtizar
ou integrar).

## As personas

Cada persona é um papel com escopo travado. Cole o arquivo da persona no início da thread,
junto com `RULES.md` e o `STATE.md` do projeto.

| Persona | Use quando | Produz |
| --- | --- | --- |
| Prototyper | Validar uma ideia/hipótese em dados reais, no Jupyter | Relatório de validação |
| Productionize | Há um protótipo validado pra virar produção | PLAN + HANDOFFs + Decisões + gabaritos |
| Implementer | Executar **um** passo do plano | Código do arquivo + teste golden |
| Bootstrapper | Início de projeto, ou mexer no Roadmap | `PROJECT.md` |
| Mapper | Precisa do mapa do código atualizado | `CODEBASE-MAP.md` |

As três primeiras são o **caminho central**. Bootstrapper e Mapper são suporte.

Não há mais Architect nem Planner: o discovery acontece no notebook (Prototyper) e o
planejamento sai do protótipo validado (Productionize). Se uma abordagem não fecha, ela
**volta pro notebook** — não escala pra um arquiteto.

## O caminho central

```text
[projeto novo]
   └─ Bootstrapper ........... cria PROJECT.md (miolo + Roadmap)
[código já existe]
   └─ python -m scripts.gsd → Mapper ... gera CODEBASE-MAP.md

[cada fase]
   Prototyper ........ Jupyter: valida a hipótese célula a célula → relatório
      └─ Productionize ... relatório → PLAN + HANDOFFs + Decisões + gabaritos
           └─ Implementer ... passo 1..N → código + teste golden em cada portão
                              último passo: integra no orquestrador + gabarito
                              end-to-end, e fecha a fase
```

O `STATE.md` atravessa o fluxo: Prototyper e Productionize devolvem um bloco
`UPDATE STATE.md` ao final; o **Implementer só atualiza o STATE no fim da fase** (os
portões verdes são o checkpoint de cada passo). Decisões duráveis e mudança de status de
fase vão **direto pro `PROJECT.md`** via bloco `UPDATE PROJECT.md` — sem rota pelo
Bootstrapper.

## Níveis e responsáveis

```text
Projeto  (context/PROJECT.md) — hub durável
   ├── miolo + Roadmap ............ Bootstrapper
   └── Decisões ................... Productionize  (via UPDATE PROJECT)

Fase N
   ├── Validação  (handovers/) .... Prototyper
   ├── Plano  (plans/fase-N-*.md) . Productionize
   ├── Gabaritos  (tests/) ........ Productionize define, Implementer escreve
   └── Passos → código ............ Implementer

Transversais (não pertencem a uma fase):
   Mapa  (context/CODEBASE-MAP.md) . Mapper
   Estado  (STATE.md) ............. você, via blocos UPDATE das personas
```

| Nível | Artefato | Path | Responsável |
| --- | --- | --- | --- |
| Projeto (hub) | PROJECT.md | `docs/gsd/context/` | Bootstrapper (miolo/Roadmap) + Productionize (Decisões) |
| Validação | Relatório de prototipagem | `docs/gsd/handovers/` | Prototyper |
| Plano | PLAN.md | `docs/gsd/plans/` | Productionize |
| Gabarito | Teste golden + `expected.json` (commitado) + fixture (gitignored) | `tests/golden/`, `tests/fixtures/` | Productionize (define) / Implementer (escreve) |
| Execução | Código | repo do projeto | Implementer |
| Mapa | CODEBASE-MAP.md | `docs/gsd/context/` | Mapper |
| Estado | STATE.md | `docs/gsd/` | você (via blocos UPDATE) |

## O que blinda a transpilação: gabaritos golden

O maior risco do caminho prototype-first é a **transpilação cega**: o protótipo funciona no
notebook, o Implementer reescreve célula por célula em vários passos, e o primeiro momento
em que a produção é exercitada é quando você roda o orquestrador lá na frente. Se quebrou, o
erro está em algum dos M passos e você não sabe qual.

A solução usa o que o protótipo já produz. O Prototyper, por hábito, audita cada célula que
toca dados (`shape`, `value_counts`, soma de controle, `print(KPI=...)`). Esses sinais
**são o gabarito**: "nesta amostra, a conciliação dá shape (1240, 8) e soma de saldo
4.812.330,55". O fluxo carrega esse gabarito adiante:

- **Productionize** colhe os sinais provados (presos a uma fatia de referência), marca cada
  passo que mexe num número como **portão**, e separa dado de valor: o valor esperado vai
  commitado em `tests/golden/fase-N/expected.json`; o dado real vira fixture local em
  `tests/fixtures/fase-N/` (**gitignored** — não vaza dado sensível pro repo).
- **Implementer**, num passo-portão, entrega o código **+ `expected.json`** (valores) **+ um
  teste golden durável** (`tests/golden/fase-N/test_<bloco>.py`) que lê os valores, roda a
  função sobre a fixture local e dá `assert`. Se a fixture não existir, o teste dá `skip`
  com instrução pra regenerá-la (`scripts/make_fixture_fase-N.py`).
- O passo de integração ganha um gabarito **end-to-end**: `assert` no KPI final da fase,
  que pega erro de fiação (ordem de chamada, config) que o teste por bloco não pega.

Resultado: você descobre a quebra **no passo M**, rodando `pytest`, não depois da fase N
rodando o orquestrador. E os goldens viram rede de regressão permanente. Quando você
re-prototipa e um número legitimamente muda, é só re-rodar o Productionize: ele recolhe os
sinais novos e re-emite os testes — você não caça valor à mão em dez arquivos.

## Como montar um prompt

No primeiro turno de uma thread, cole nesta ordem:

1. `RULES.md` (as regras fixas)
2. A persona do papel atual (ex: `personas/productionizer.md`)
3. O `STATE.md` do projeto + o que a persona pede (ver quadro abaixo)
4. Seu pedido

O que entra no item 3, por persona:

| Persona | Cole junto (além de RULES + STATE) |
| --- | --- |
| Prototyper | Sua hipótese/pergunta + caminho ou amostra dos dados reais |
| Productionize | Relatório do Prototyper + o notebook validado + `PROJECT.md` + `CODEBASE-MAP.md` |
| Implementer | O HANDOFF do passo + a saída do `pack` que o HANDOFF pede |
| Bootstrapper | Descrição do projeto (modo "novo projeto"), ou `PROJECT.md` atual + o delta |
| Mapper | `.temp/codebase-snapshot.txt` (de `python -m scripts.gsd`); opcional: CODEBASE-MAP anterior |

Em cada turno seguinte, cole no **final** do pedido o sufixo dinâmico (está no fim do
`RULES.md`): ele reforça os marcadores de artefato, que são a primeira regra que o modelo
esquece em threads longas.

Ao receber a resposta, extraia cada artefato copiando o conteúdo **entre**
`<!-- INICIO: path -->` e `<!-- FIM: path -->` e salvando no `path` indicado pelo próprio
marcador. Se o destino é `.md` e o conteúdo não começa com `#`, adicione um H1 no topo
(regra MD041 — detalhe na seção 2.4.1 do manual).

## O comando `pack`: a persona te dá o comando, não a lição de casa

As personas costumam precisar ver um módulo inteiro ou um schema. Em vez de te mandar
"cole `main.py`, cole `conciliacao.py`", elas emitem **um comando** pra você rodar e colar
a saída:

```text
python -m scripts.gsd pack src/orquestrador.py src/conciliacao/cop.py
```

O `pack` lê cada arquivo (pasta vira os arquivos de texto dentro dela, recursivo), embrulha
no formato `=== ARQUIVO: path ===` que as personas esperam, escreve em `.temp/pack.txt` e
ecoa na stdout — você seleciona no terminal e cola. Acentos saem corretos mesmo no console
do Windows. Schemas continuam vindo de `python -m scripts.gsd` (precisam do registry em
runtime); quando a persona precisa dos dois, ela te dá as duas linhas.

## Instalar num projeto de trabalho

1. Copie o conteúdo de `templates/` para a raiz do repo de trabalho: vira `docs/gsd/`, mais `RULES.md` e `manual-copilot-windows.md` à mão para colar/consultar.
2. Copie `scripts/gsd/` para a raiz do repo de trabalho (precisa ser importável como `scripts.gsd`).
3. Garanta que `.temp/` **e** `tests/fixtures/` estão no `.gitignore` do projeto — snapshot, `pack` e fixtures podem conter dados reais. Os valores esperados (`tests/golden/**/expected.json`) são commitados; o dado, não.
4. Preencha `PROJECT.md` à mão (miolo + Roadmap), ou rode o Bootstrapper (modo "novo projeto"). Não há mais `ROADMAP.md` nem pasta `adr/` — Roadmap e Decisões são seções do `PROJECT.md`.
5. Rode `python -m scripts.gsd` e passe o resultado pro Mapper para gerar o `CODEBASE-MAP.md`.
6. As pastas `tests/golden/fase-N/` (commitada: testes + `expected.json`) e `tests/fixtures/fase-N/` (gitignored: dado real) nascem conforme o Productionize planeja cada fase.

## Os scripts (`scripts/gsd/`)

Dois subcomandos:

Snapshot do código (para o Mapper) — árvore + assinaturas + schemas:

```bash
python -m scripts.gsd
```

Empacotador de contexto (para qualquer persona que peça arquivos) — embrulha arquivos/pastas
pra colar no chat:

```bash
python -m scripts.gsd pack src/conciliacao/ src/orquestrador.py
```

Porta runtime (dentro do `main.py` do pipeline) — registra DataFrames para popular a seção
de schemas do snapshot:

```python
from scripts.gsd import registry, snapshot_completo

registry.add("balancete", df_balancete)
registry.add("cop", df_cop)
# ... no fim do pipeline ...
snapshot_completo()
```

Saída do snapshot: `.temp/codebase-snapshot.txt` (três seções: ÁRVORE, ASSINATURAS, SCHEMAS).
Saída do pack: `.temp/pack.txt` (+ stdout).

Há ainda `snapshot_architect()`, que gera `.temp/architect-snapshot.txt` com **amostras
reais** dos DataFrames (3 linhas cada), útil pro Prototyper quando precisa ver dado real.
**Esse arquivo pode conter PII / valores financeiros — mantenha local, não cole em chat
externo e não comite.**

## Referência

O `templates/manual-copilot-windows.md` documenta o porquê de cada regra: anti-aninhamento de
backtick, marcadores HTML, trava de escopo por SAÍDAS, as camadas de contexto e a tabela
completa de sintoma → decisão de design. Leia quando uma regra parecer arbitrária.
