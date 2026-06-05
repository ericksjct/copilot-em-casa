# Manual de Formatação de Prompts — Copilot do Windows

> Referência prescritiva para construir prompts no Copilot do Windows sem
> quebrar parser, sem perder contexto em threads longas e sem deixar o modelo
> antecipar entregas. Audiência: o autor humano e qualquer LLM lendo este
> arquivo como contexto de sessão.

---

## 1. Contexto e Premissas

### 1.1 O que é o Copilot do Windows

Chat com LLM (GPT-4 por trás) embutido no Windows. Renderiza markdown na
resposta. Não escreve em disco, não tem comandos slash, não roda agentes
paralelos, não tem memória entre threads, não tem indexação semântica de
codebase, não tem Plan Mode nativo (esse é do GitHub Copilot no VS Code).

O usuário humano é o "runtime": copia, cola, salva arquivos manualmente.

### 1.2 Por que este manual existe

Dois problemas crônicos motivam todas as regras abaixo:

- **Parser frágil:** certas construções de markdown quebram a renderização ou
  poluem visualmente a UI.
- **Instruction drift:** em threads longas, o modelo esquece instruções dadas
  no início. Sem reinjeção, a aderência cai.

Cada regra deste manual corrige um sintoma observado empiricamente. A
seção 9 lista a correspondência sintoma → decisão.

### 1.3 Como ler este manual

- Seções 2 e 3 são **regras de sintaxe** (o que escrever).
- Seções 4 e 5 são **regras de arquitetura de sessão** (como estruturar a
  conversa).
- Seção 6 traz **templates prontos** para colar.
- Seção 7 traz **exemplos comentados** de prompts bem e mal formatados.
- Seção 8 é o **checklist de validação** antes de enviar.
- Seção 9 documenta o **histórico de descobertas** (sintoma → decisão).

---

## 2. Fundamentos de Renderização — O Que NÃO Fazer

Três proibições absolutas. Violar qualquer uma delas quebra a renderização ou
gera ruído visual irrecuperável.

### 2.1 Não aninhe blocos de crases triplas

Qualquer combinação de triple-backtick dentro de triple-backtick quebra o
parser. O backtick interno fecha o externo cedo demais, e o restante da
resposta vira lixo visual.

Exemplos que quebram:

- Bloco sem linguagem dentro de bloco sem linguagem.
- `python` dentro de `markdown`.
- `python` dentro de `python`.

**Solução:** use os delimitadores de artefato (seção 3.2) quando precisar
encapsular conteúdo que contém blocos de código.

### 2.2 Não inicie linhas com `>`

O caractere `>` no começo de linha vira blockquote. Múltiplos `>` aninhados
(ex: `>>>>>`) viram blockquotes aninhados, gerando barras verticais
descendentes em escada.

Isso elimina `>>>>>` como delimitador de artefato.

### 2.3 Não use headers estilo Setext

Headers com `===` ou `---` abaixo do texto (Setext) violam o markdownlint
(MD003) e geram inconsistência de renderização. Use sempre ATX (`##`, `###`).

### 2.4 No máximo um `#` (H1) por resposta

Regra MD025 (single-h1). O sintoma específico no Copilot: quando a resposta do
modelo tem um título próprio com `#` e o artefato gerado também começa com
`#`, a UI renderiza dois títulos de hierarquia máxima na mesma resposta. Fica
visualmente confuso e o markdownlint reclama quando o conteúdo é salvo.

Regras práticas:

- A resposta do modelo na thread, se tiver título, usa exatamente um `#`. Nada
  mais.
- Se o artefato encapsulado entre `<!-- INICIO -->` e `<!-- FIM -->` precisa
  de título próprio, ele entra como `##` (H2) e desce em hierarquia a partir
  daí.
- Alternativa preferida: o título do artefato fica no nome do marcador
  (`<!-- INICIO: nome_do_artefato -->`) e o conteúdo começa direto em `##`.
- Quando o artefato é um arquivo `.md` standalone que precisa de `#` no topo
  (ex: README), a resposta do modelo na thread **não usa `#` em lugar
  nenhum** — só prosa curta e o artefato.

A regra é injetada no STATE.md (seção 6.1) para sobreviver ao instruction
drift.

#### 2.4.1 H1 sintético na extração para arquivo

Conflito conhecido entre MD025 (single-h1) e MD041 (first-line-heading):

- MD025 proíbe múltiplos `#` na resposta.
- MD041 exige que arquivos `.md` comecem com `#` na primeira linha.

Quando o artefato gerado pelo Copilot não tem `#` natural (ex: DDL SQL,
configuração YAML, schema JSON, snippet técnico) e é extraído pra um arquivo
`.md` standalone, o markdownlint reclama de MD041.

Solução: **na extração**, o usuário envelopa o artefato com um H1 sintético
derivado do nome do marcador. O Copilot não gera esse H1 — ele é
responsabilidade do passo de salvamento.

Padrão de extração:

```text
Marcador no Copilot: <!-- INICIO: ddl_fact_balancete -->

Arquivo extraído (ddl_fact_balancete.md):
# DDL — fact_balancete

[conteúdo original do artefato]
```

Regras de derivação do H1 sintético:

- Snake_case do marcador vira título legível (`ddl_fact_balancete` → `DDL — fact_balancete`).
- Para artefatos que não são documentação (ex: arquivo `.sql` puro), não
  salve como `.md`. Salve com a extensão nativa (`.sql`, `.yaml`, `.py`)
  e o markdownlint nem entra em cena.

Decisão prática: se o artefato é código puro, salve com extensão nativa. Se
é documentação técnica que mistura prosa e código, salve como `.md` e
adicione o H1 sintético na extração.

### 2.5 Espaçamento estrutural — linhas em branco obrigatórias

O Copilot tem viés de **compactação**: gruda heading com texto, lista com
heading, code fence com heading. Renderiza bem no chat mas viola três regras
do markdownlint quando salvo como arquivo:

- **MD022** — headings precisam de linha em branco **antes E depois**.
- **MD031** — code fences (` ``` `) precisam de linha em branco antes E
  depois.
- **MD032** — listas precisam de linha em branco antes E depois.

Padrão correto:

```text
Parágrafo anterior.

## Heading

Parágrafo abaixo do heading.

- Item de lista
- Outro item

Parágrafo abaixo da lista.

```python
def foo():
    pass
```

Parágrafo abaixo do bloco de código.
```

Padrão errado (compactado, viola lint):

```text
Parágrafo anterior.
## Heading
- Item de lista
- Outro item
```python
def foo():
    pass
```
Parágrafo abaixo.
```

A regra precisa estar no STATE.md porque o viés de compactação é forte e o
modelo recai nele rapidamente.

### 2.6 Sem links com destino vazio (MD042)

O Copilot tem tendência a gerar badges e links placeholder com destino
vazio. Exemplos do antipadrão:

```text
[![Build](https://img.shields.io/badge/build-passing-green)]()
[Documentação](#)
[Link](<>)
```

Todos quebram MD042. Regras de substituição:

- Se o link/badge é decorativo e você não vai usar de verdade: **omita
  completamente**.
- Se é placeholder para preencher depois: use URL plausível
  (`https://example.com/TODO`) ou marque como `[texto](LINK_TODO)` e troque
  manualmente.
- Para badges de README: use shields.io com URL real do projeto ou omita até
  ter URL.

A regra é especialmente relevante em geração de README, onde o modelo
"decora" com badges genéricos.

---

## 3. Sintaxe Segura — O Que Fazer

### 3.1 Blocos de código: `text` vs linguagem nomeada

O botão "copiar" aparece quando o bloco tem **linguagem nomeada**. Isso é
ótimo para código que vai pro projeto, mas vira poluição visual para snippets
ilustrativos curtos.

Regra de decisão:

| Situação                                                   | Marcação        |
| ---------------------------------------------------------- | --------------- |
| Código que vai pro projeto (arquivo completo, copiar tudo) | `python`, `sql` |
| Comando shell que será executado                           | `bash`, `pwsh`  |
| Snippet curto ilustrativo (1-5 linhas, didático)           | `text`          |
| Árvore de arquivos com box-drawing                         | `text`          |
| Log, output de terminal                                    | `text`          |

`text` foi escolhido em vez de bloco sem linguagem porque o markdownlint
(MD040) exige linguagem declarada e `text` não dispara validação semântica
do conteúdo interno.

### 3.2 Delimitadores de artefato: comentários HTML

Para conteúdo durável (HANDOFF, PLAN, teste golden, arquivos de código completos),
encapsule com comentários HTML:

```text
<!-- INICIO: nome_do_artefato -->
... conteúdo, incluindo blocos ```python ...
<!-- FIM: nome_do_artefato -->
```

Por que funciona:

- Comentários HTML não são triple-backtick → não há aninhamento de
  delimitadores iguais.
- O Copilot trata como texto literal (não interpreta como tag).
- Permitem ter ` ```python ` dentro deles sem quebrar nada.
- Visualmente identificáveis para extração manual.

Confirmado em teste: `python` dentro dos delimitadores funciona, com botão
copiar ativo.

### 3.3 Listas: hífen obrigatório

O modelo tem viés forte para `*` em listas. Isso conflita com convenções de
markdown lint (MD004) e gera inconsistência quando o mesmo documento mistura
`-` e `*`.

Regra: **só hífen.** Declare isso explicitamente no prompt (camada A,
seção 4.1), porque sem declaração negativa o modelo volta ao default.

### 3.4 Headers: só ATX

```text
## Título nível 2
### Subtítulo nível 3
```

Nunca:

```text
Título nível 2
==============
```

---

## 4. Arquitetura de Prompt — Resiliência de Contexto

O modelo esquece instruções em threads longas. A solução é dividir as
instruções em duas camadas com cadências de injeção diferentes.

### 4.1 Camada A — Contexto Estático (STATE.md)

Colado **uma vez**, no início de cada thread nova. Define regras invariantes
e o protocolo de entregas.

Conteúdo típico:

- Regras de sintaxe (listas com hífen, marcação de código, anti-aninhamento).
- Trava de escopo (ver seção 5).
- Lista de SAÍDAS numeradas, com estado (ATIVADA / BLOQUEADA).

Template completo na seção 6.1.

### 4.2 Camada B — Sufixo Dinâmico

Adicionado ao **final de cada novo pedido** dentro da thread.

Por que existe: instruções sobre "strings literais" (como os marcadores de
artefato) são as primeiras que o modelo esquece. Se você não pedir o marcador
exato no turno atual, ele não gera.

Formato:

```text
Gere o artefato da fatia atual obrigatoriamente dentro dos marcadores
<!-- INICIO: [nome_do_artefato] --> e <!-- FIM: [nome_do_artefato] -->.
```

### 4.3 Por que duas camadas

| Camada | Conteúdo               | Frequência         | Função                       |
| ------ | ---------------------- | ------------------ | ---------------------------- |
| A      | Regras gerais + escopo | 1× por thread      | Define a sessão              |
| B      | Marcadores de artefato | 1× por turno       | Reforça regras voláteis      |

Camada A sozinha falha após ~5-10 turnos. Camada B sozinha não estabelece
escopo. Juntas, mantêm aderência consistente.

---

## 5. Controle Comportamental — Anti Scope Creep

### 5.1 O sintoma

Quando você pede um plano, o Copilot tende a entregar todos os 8 passos com
24 contratos técnicos de uma vez. A instrução "pare após entregar essa fatia"
não é suficiente — o modelo ignora.

### 5.2 A solução: trava por SAÍDAS numeradas

Estruture o trabalho como uma lista numerada de SAÍDAS, marcadas com estado:

```text
Protocolo de Entregas:
- SAÍDA 1 (ATIVADA): Esqueleto do parser
- SAÍDA 2 (BLOQUEADA): Implementação dos tokenizers
- SAÍDA 3 (BLOQUEADA): Testes de regressão
- SAÍDA 4 (BLOQUEADA): Documentação de API
```

O modelo respeita formulários restritivos. Marcar SAÍDA 2 em diante como
`(BLOQUEADA)` impede a antecipação. Quando terminar SAÍDA 1, você edita o
STATE.md (na sua cabeça ou em arquivo local) e reinjeta com SAÍDA 2 como
`(ATIVADA)`.

### 5.3 Regra da fatia única

Combine a trava com instrução explícita na camada A:

> TRAVA DE ESCOPO: Gere APENAS o conteúdo da SAÍDA (ATIVADA). É
> terminantemente proibido antecipar saídas (BLOQUEADAS).

### 5.4 Checkpoint no final de cada fatia

Termine respostas parciais com pergunta curta: "Prosseguimos para SAÍDA 2?".
Isso devolve o controle ao usuário e evita continuação automática.

---

## 6. Templates Prontos

### 6.1 Template de STATE.md (Camada A)

Cole isto no início de cada thread nova, ajustando o protocolo de entregas:

<!-- INICIO: template_state_md -->

```text
=== REGRAS DO SISTEMA (OBEDIÊNCIA ESTRITA) ===

1. TRAVA DE ESCOPO
   Gere APENAS o conteúdo da SAÍDA (ATIVADA). É terminantemente proibido
   antecipar saídas (BLOQUEADAS).

2. LISTAS
   Use estritamente o caractere `-` (hífen). O uso de `*` (asterisco) é
   proibido.

3. CÓDIGO
   - Use marcação `text` para exemplos, árvores de arquivo, logs e
     snippets curtos.
   - Use marcação com linguagem (python, sql, bash, etc.) apenas para
     arquivos completos copiáveis.
   - Nunca aninhe blocos de código (triple-backtick dentro de
     triple-backtick).

4. HEADERS
   - Use somente sintaxe ATX (## e ###). Proibido Setext (=== ou ---).
   - No máximo UM `#` (H1) por resposta. Se o artefato precisa de título,
     ele entra como `##` (H2). Se o artefato é um arquivo .md que exige `#`
     no topo, a resposta na thread não usa `#` em lugar nenhum.

5. ARTEFATOS DURÁVEIS
   Encapsule entre marcadores HTML:
   <!-- INICIO: nome_do_artefato -->
   ... conteúdo ...
   <!-- FIM: nome_do_artefato -->

6. ESPAÇAMENTO ESTRUTURAL
   Sempre uma linha em branco ANTES E DEPOIS de:
   - Cada heading (## e ###).
   - Cada bloco de código (```).
   - Cada lista.
   Não compacte. Markdownlint MD022, MD031, MD032 exigem essa estrutura.

7. LINKS E BADGES
   Proibido gerar links com destino vazio (`[texto]()` ou `[texto](#)`).
   Se não tiver URL real, omita o link. MD042 quebra com link vazio.

==============================================

Protocolo de Entregas:
- SAÍDA 1 (ATIVADA): [descrição do objetivo atual]
- SAÍDA 2 (BLOQUEADA): [próximo objetivo]
- SAÍDA 3 (BLOQUEADA): [objetivo seguinte]
```

<!-- FIM: template_state_md -->

### 6.2 Template de Sufixo Dinâmico (Camada B)

Cole no final de cada novo pedido na thread:

<!-- INICIO: template_sufixo_dinamico -->

```text
Gere o artefato da fatia atual obrigatoriamente dentro dos marcadores
<!-- INICIO: [nome_do_artefato] --> e <!-- FIM: [nome_do_artefato] -->.
PARE após entregar essa fatia. Aguarde minha resposta antes de qualquer
outra coisa.
```

<!-- FIM: template_sufixo_dinamico -->

### 6.3 Template de persona

Para tarefas que se beneficiam de papel definido (Prototyper, Productionize,
Implementer, etc.). Cole junto com o STATE.md no primeiro turno.

<!-- INICIO: template_persona -->

```text
=== PERSONA: [Nome] ===

OBJETIVO
[Uma frase descrevendo o que essa persona produz.]

ENTRADAS ESPERADAS
- [Lista do que o usuário fornecerá]

SAÍDAS NUMERADAS (cada uma é uma fatia independente)
1. [Primeira entrega]
2. [Segunda entrega]
3. [Terceira entrega]

REGRA DE DUPLICAÇÃO
Cada saída cobre conteúdo distinto. Proibido repetir conteúdo entre saídas.

REGRA DE FATIA ÚNICA
Entregue apenas a SAÍDA marcada como (ATIVADA) no STATE.md.
Termine com "Prosseguimos para SAÍDA N+1?" e aguarde.

=======================
```

<!-- FIM: template_persona -->

---

## 7. Exemplos Comentados

### 7.1 Pedido mal formatado (anti-padrão)

<!-- INICIO: exemplo_ruim -->

```text
Me gera o projeto completo de parser de markdown em Python, com testes,
documentação, exemplos de uso e tudo o que precisar. Pode caprichar.
```

<!-- FIM: exemplo_ruim -->

Problemas:

- Sem trava de escopo → modelo despeja tudo de uma vez.
- Sem marcação de artefato → resposta longa quebra a renderização no meio.
- "Pode caprichar" → convite ao scope creep.
- Sem persona, sem SAÍDAS → sem critério de parada.

### 7.2 Pedido bem formatado

<!-- INICIO: exemplo_bom -->

```text
[STATE.md já colado no início da thread, com:
- SAÍDA 1 (ATIVADA): Esqueleto do parser (assinatura das funções,
  docstrings, sem implementação)
- SAÍDA 2 (BLOQUEADA): Implementação dos tokenizers
- SAÍDA 3 (BLOQUEADA): Testes
]

Gere a SAÍDA 1 agora.

Gere o artefato da fatia atual obrigatoriamente dentro dos marcadores
<!-- INICIO: parser_esqueleto --> e <!-- FIM: parser_esqueleto -->.
PARE após entregar essa fatia. Aguarde minha resposta antes de qualquer
outra coisa.
```

<!-- FIM: exemplo_bom -->

Por que funciona:

- STATE.md estabelece regras invariantes da sessão.
- SAÍDAS numeradas com estados (ATIVADA / BLOQUEADA) impedem antecipação.
- Sufixo dinâmico reinjeta a regra de marcadores de artefato.
- "PARE após entregar" + "aguarde minha resposta" cria critério de parada
  explícito.

### 7.3 Resposta esperada do modelo (formato correto)

<!-- INICIO: exemplo_resposta -->

```text
Entregando SAÍDA 1: Esqueleto do parser.

<!-- INICIO: parser_esqueleto -->

```python
def tokenize(source: str) -> list[Token]:
    """Converte string fonte em lista de tokens.

    Args:
        source: texto markdown bruto.
    Returns:
        Lista de tokens preservando ordem.
    """
    ...
```

<!-- FIM: parser_esqueleto -->

Prosseguimos para SAÍDA 2?
```

<!-- FIM: exemplo_resposta -->

Observe:

- O artefato está cercado pelos marcadores corretos.
- O bloco `python` dentro dos marcadores funciona (sem aninhamento de
  triple-backtick com outro triple-backtick).
- Checkpoint no final devolve o controle ao usuário.

### 7.4 Anti-padrão: aninhamento de backtick

<!-- INICIO: exemplo_aninhamento -->

```text
Não faça isto (vai quebrar a renderização):

```markdown
Aqui está um exemplo de código:
```python
def foo():
    pass
```
```
```

<!-- FIM: exemplo_aninhamento -->

O segundo triple-backtick (` ```python `) fecha o primeiro (` ```markdown `)
prematuramente. O terceiro triple-backtick passa a ser interpretado como
abertura de novo bloco, e tudo desanda.

**Correção:** use marcadores HTML para encapsular o exemplo externo.

---

## 8. Checklist de Validação

### 8.1 Antes de enviar o prompt

- [ ] STATE.md foi colado no início da thread (se for o primeiro turno)?
- [ ] O pedido referencia uma SAÍDA específica e seu estado é (ATIVADA)?
- [ ] As demais SAÍDAS estão marcadas como (BLOQUEADA)?
- [ ] O sufixo dinâmico (camada B) está no final do pedido?
- [ ] O nome do artefato no sufixo está preenchido corretamente?

### 8.2 Ao receber a resposta

- [ ] O artefato veio dentro dos marcadores `<!-- INICIO -->` e
      `<!-- FIM -->`?
- [ ] Não há aninhamento de triple-backtick?
- [ ] Listas usam `-`, não `*`?
- [ ] Headers estão em ATX (`##`, `###`), não Setext?
- [ ] O modelo parou após a fatia única e fez checkpoint?
- [ ] Não há antecipação de SAÍDAS bloqueadas?

### 8.3 Ao extrair o artefato para arquivo

- [ ] A extensão escolhida é a nativa do conteúdo (`.sql`, `.py`, `.yaml`)
      sempre que possível, evitando o conflito com markdownlint?
- [ ] Se o destino é `.md` e o artefato não tem `#` natural, adicione H1
      sintético derivado do nome do marcador no topo do arquivo (regra
      2.4.1)?
- [ ] O conteúdo entre `<!-- INICIO -->` e `<!-- FIM -->` foi copiado sem
      os próprios marcadores?

Se qualquer item da seção 8.2 falhar, reinjete a camada A no próximo turno
e refaça o pedido.

---

## 9. Histórico de Descobertas — Sintoma → Decisão de Design

Cada problema observado empiricamente moldou uma decisão. Esta tabela é a
justificativa das regras acima.

| Sintoma observado                                          | Decisão de design                                                                 |
| ---------------------------------------------------------- | --------------------------------------------------------------------------------- |
| Aninhamento de triple-backtick quebra renderização         | Marcadores `<!-- INICIO -->` / `<!-- FIM -->` em vez de blocos aninhados          |
| `>>>>>` como delimitador vira blockquote aninhado          | Substituído por comentários HTML                                                  |
| Botões "copiar" excessivos poluem a UI                     | Marcação `text` para snippets, linguagem nomeada só para arquivos copiáveis       |
| Modelo despeja todo o projeto de uma vez                   | Trava por SAÍDAS numeradas com estados ATIVADA / BLOQUEADA                        |
| Instrução "pare após entregar" sozinha falha               | Combinada com SAÍDAS bloqueadas (forma restritiva, não imperativa)                |
| Modelo esquece marcadores de artefato após poucos turnos   | Sufixo dinâmico reinjetado em cada pedido (camada B)                              |
| Sem memória entre threads                                  | STATE.md colado no início de cada thread nova (camada A)                          |
| Modelo usa `*` em listas por default                       | Regra negativa explícita na camada A                                              |
| Headers Setext (`===`) violam markdownlint MD003           | Padrão obrigatório ATX (`##`)                                                     |
| Dois `#` H1 na mesma resposta (título + artefato .md)      | Regra MD025: máximo 1 H1 por resposta; artefato usa H2 ou nome no marcador        |
| Headings/listas/code fences grudados sem blank line        | Regra de espaçamento explícita no STATE.md (MD022, MD031, MD032)                  |
| Badges placeholder com `]()` vazio em READMEs              | Regra negativa: proibido link com destino vazio; omitir se não houver URL (MD042) |
| Artefato sem H1 natural (DDL, YAML) salvo como .md         | H1 sintético na extração derivado do nome do marcador; ou usar extensão nativa (MD041) |
| MD060 (table-column-style) reclama de padding de tabela    | Decisão de ambiente, não de prompt: desabilitar MD060 no `.markdownlint.json` do projeto (`"MD060": false`); custo cognitivo de manter padding perfeito é desproporcional |
| Bloco ` ```markdown ` faz lint validar conteúdo interno    | Usar `text` quando exemplo interno tem headers                                    |
| Resposta longa mistura blocos e texto, parser "se perde"   | Resumos curtos na thread + artefatos longos cercados por marcadores               |
| Modelo confunde fronteira entre artefato e prosa           | Delimitadores HTML explícitos servem de âncora visual e semântica                 |

---

## 10. Princípio Metodológico

A lição transversal de toda a investigação que gerou este manual:

> Suposições sobre comportamento de ferramenta sem teste empírico geram
> retrabalho.

O loop que funcionou consistentemente:

1. Identifica o sintoma específico (com print ou descrição do efeito).
2. Hipotetiza causa raiz.
3. Cria prompt de teste mínimo que isola a variável.
4. Roda o teste no Copilot real.
5. Aplica o aprendizado de volta no sistema.

Toda regra deste manual passou por esse ciclo. Quando adicionar regras
novas, faça o mesmo: teste antes de prescrever.
