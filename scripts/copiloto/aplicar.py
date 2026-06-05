"""
Aplica a saída de uma persona: lê o texto raw e materializa os artefatos que ela
delimitou com marcadores HTML `<!-- INICIO: alvo -->` ... `<!-- FIM: alvo -->`.

Fonte do texto (híbrida): se `llm_output.md` na raiz do repo contém marcadores,
usa ele; senão, lê do clipboard. Depois de gravar (--write) a partir do
`llm_output.md`, o arquivo é zerado pro próximo uso.

O que o script faz com cada bloco, pelo nome do alvo:

  - alvo termina em `.md`  -> grava o arquivo .md EXATAMENTE como a persona
    entregou, com os próprios marcadores dentro do arquivo. Se o corpo não
    começa com um título `# ` (H1), insere um H1 sintético derivado do nome do
    arquivo (regra MD041). Desligável com --sem-h1.

  - alvo `UPDATE STATE.md` / `UPDATE PROJECT.md`  -> NÃO é arquivo inteiro: é um
    bloco de updates por seção. O script faz merge automático no arquivo alvo
    (docs/copiloto/STATE.md e docs/copiloto/contexto/PROJECT.md), seção a seção,
    pelos verbos atualizar / substituir / adicionar / remover.

  - alvo de código/dado (`.py`, `.sql`, `.json`, `.yaml`, ...)  -> IGNORA e
    avisa. Código é criado à mão pelo usuário (fora do escopo do script).

  - qualquer outro marcador (ilustrativo, sem cara de arquivo)  -> ignora e lista.

Por padrão roda em DRY-RUN: só mostra o que faria. Use --write pra gravar.

    python -m scripts.copiloto aplicar            # preview (dry-run)
    python -m scripts.copiloto aplicar --write     # grava de fato
"""
from __future__ import annotations

import difflib
import re
import subprocess
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

from scripts.copiloto.paths import RAIZ_REPO

# ----------------------------------------------------------------------
# Constantes
# ----------------------------------------------------------------------

ARQUIVO_LLM_OUTPUT: Path = RAIZ_REPO / "llm_output.md"

# Onde moram os arquivos vivos do fluxo (alvos dos blocos UPDATE).
ALVO_STATE: Path = RAIZ_REPO / "docs" / "copiloto" / "STATE.md"
ALVO_PROJECT: Path = RAIZ_REPO / "docs" / "copiloto" / "contexto" / "PROJECT.md"

VERBOS = ("atualizar", "substituir", "adicionar", "remover")

# Extensões que o script grava (.md) vs. as que ignora (código/dado, à mão).
EXT_MARKDOWN = frozenset({".md"})

_RE_INICIO = re.compile(r"<!--\s*INICIO:\s*(?P<nome>.+?)\s*-->")
_RE_FIM = re.compile(r"<!--\s*FIM:\s*(?P<nome>.+?)\s*-->")
_RE_DIRETIVA = re.compile(
    r"^\s*[-*]?\s*(?P<sec>[^:|()]+?)\s*\((?P<verbo>"
    + "|".join(VERBOS)
    + r")\)\s*:\s*(?P<inline>.*)$",
    re.IGNORECASE,
)
_RE_CABECALHO = re.compile(r"^(#{1,6})\s+(?P<titulo>.*)$")

# Conteúdo de reset do llm_output.md depois de uma gravação bem-sucedida.
TEMPLATE_LLM_OUTPUT = """<!-- Cole AQUI a resposta completa da persona (substituindo este comentário). -->
<!-- Depois rode:  python -m scripts.copiloto aplicar          (preview) -->
<!--               python -m scripts.copiloto aplicar --write  (grava)   -->
"""


# ----------------------------------------------------------------------
# Modelo
# ----------------------------------------------------------------------

@dataclass
class Bloco:
    """Um bloco delimitado por marcadores no texto raw."""

    nome: str
    corpo: list[str]


@dataclass
class Acao:
    """Uma ação planejada (e talvez executada) sobre um arquivo."""

    rotulo: str  # "novo" | "sobrescreve" | "inalterado" | "merge" | "ignora-código" | "ignora"
    alvo: str  # path relativo ou nome do marcador
    diff: list[str] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)


# ----------------------------------------------------------------------
# Extração de blocos
# ----------------------------------------------------------------------

def extrair_blocos(texto: str) -> list[Bloco]:
    """
    Extrai os blocos `<!-- INICIO: nome -->` ... `<!-- FIM: nome -->` do texto.

    Casa cada INICIO com o PRÓXIMO FIM de mesmo nome — assim marcadores
    diferentes que apareçam no corpo (ex: exemplos dentro de um .md) ficam
    preservados verbatim, sem confundir o parser.
    """
    linhas = texto.splitlines()
    blocos: list[Bloco] = []
    i = 0
    n = len(linhas)
    while i < n:
        m_ini = _RE_INICIO.search(linhas[i])
        if not m_ini:
            i += 1
            continue
        nome = m_ini.group("nome").strip()
        # Procura o FIM correspondente (mesmo nome) à frente.
        j = i + 1
        fim = -1
        while j < n:
            m_fim = _RE_FIM.search(linhas[j])
            if m_fim and m_fim.group("nome").strip() == nome:
                fim = j
                break
            j += 1
        if fim == -1:
            # INICIO sem FIM: ignora esse marcador e segue.
            i += 1
            continue
        blocos.append(Bloco(nome=nome, corpo=linhas[i + 1 : fim]))
        i = fim + 1
    return blocos


def _tem_marcador(texto: str) -> bool:
    return _RE_INICIO.search(texto) is not None


# ----------------------------------------------------------------------
# Classificação do alvo
# ----------------------------------------------------------------------

def _extensao(nome: str) -> str:
    """Extensão do último segmento do nome do marcador (ou '' se não tiver)."""
    base = nome.replace("\\", "/").split("/")[-1]
    ponto = base.rfind(".")
    return base[ponto:].lower() if ponto > 0 else ""


def classificar(nome: str) -> str:
    """
    Retorna o tipo do alvo:
      'update_state' | 'update_project' | 'md' | 'codigo' | 'ignora'
    """
    if nome == "UPDATE STATE.md":
        return "update_state"
    if nome == "UPDATE PROJECT.md":
        return "update_project"
    ext = _extensao(nome)
    if ext in EXT_MARKDOWN:
        return "md"
    if ext:  # tem extensão, mas não é .md -> código/dado, criado à mão
        return "codigo"
    return "ignora"


# ----------------------------------------------------------------------
# Montagem do arquivo .md (verbatim + marcadores + H1 sintético)
# ----------------------------------------------------------------------

def _corpo_limpo(corpo: list[str]) -> list[str]:
    """Remove linhas em branco no começo e no fim do corpo, preserva o miolo."""
    ini, fim = 0, len(corpo)
    while ini < fim and not corpo[ini].strip():
        ini += 1
    while fim > ini and not corpo[fim - 1].strip():
        fim -= 1
    return corpo[ini:fim]


def _primeira_linha_util(corpo: list[str]) -> str:
    for linha in corpo:
        if linha.strip():
            return linha
    return ""


def _titulo_sintetico(nome: str) -> str:
    """Deriva um título legível do nome do arquivo (stem, separadores -> espaço)."""
    base = nome.replace("\\", "/").split("/")[-1]
    stem = base[: base.rfind(".")] if "." in base else base
    return stem.replace("-", " ").replace("_", " ").strip()


def montar_md(nome: str, corpo: list[str], *, com_h1: bool = True) -> str:
    """
    Monta o conteúdo final do arquivo .md: marcadores no arquivo, corpo verbatim
    e, se faltar um H1 e com_h1=True, um título sintético logo após o INICIO.
    """
    corpo = _corpo_limpo(corpo)
    partes: list[str] = [f"<!-- INICIO: {nome} -->", ""]

    primeira = _primeira_linha_util(corpo)
    falta_h1 = not primeira.startswith("# ")
    if com_h1 and falta_h1:
        partes.append(f"# {_titulo_sintetico(nome)}")
        partes.append("")

    partes.extend(corpo)
    partes.extend(["", f"<!-- FIM: {nome} -->", ""])
    return "\n".join(partes)


# ----------------------------------------------------------------------
# Merge dos blocos UPDATE por seção
# ----------------------------------------------------------------------

def _normalizar(texto: str) -> str:
    """minúsculas + sem acento, pra casar nomes de seção tolerando variação."""
    sem_acento = "".join(
        c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c)
    )
    return sem_acento.strip().lower()


def _fatiar_secoes(linhas: list[str]) -> tuple[list[str], list[tuple[str, list[str]]]]:
    """
    Quebra um markdown em (preâmbulo, [(linha_do_header_##, corpo), ...]).
    Opera no nível `## ` (seções de STATE.md / PROJECT.md).
    """
    preambulo: list[str] = []
    secoes: list[tuple[str, list[str]]] = []
    atual_header: str | None = None
    atual_corpo: list[str] = []
    for linha in linhas:
        if linha.startswith("## "):
            if atual_header is None:
                pass
            else:
                secoes.append((atual_header, atual_corpo))
            atual_header = linha
            atual_corpo = []
        elif atual_header is None:
            preambulo.append(linha)
        else:
            atual_corpo.append(linha)
    if atual_header is not None:
        secoes.append((atual_header, atual_corpo))
    return preambulo, secoes


def _nome_secao(header: str) -> str:
    return header[3:].strip()  # tira "## "


def _parsear_diretivas(corpo: list[str]) -> list[tuple[str, str, list[str]]]:
    """
    Lê o corpo do bloco UPDATE e devolve [(secao, verbo, payload_linhas), ...].
    Uma diretiva começa numa linha 'Seção (verbo): inline' e abarca as linhas
    seguintes até a próxima diretiva.
    """
    diretivas: list[tuple[str, str, list[str]]] = []
    atual: tuple[str, str, list[str]] | None = None
    for linha in corpo:
        m = _RE_DIRETIVA.match(linha)
        if m:
            if atual is not None:
                diretivas.append(atual)
            inline = m.group("inline").strip()
            payload = [inline] if inline else []
            atual = (m.group("sec").strip(), m.group("verbo").lower(), payload)
        elif atual is not None:
            atual[2].append(linha)
    if atual is not None:
        diretivas.append(atual)
    # Remove linhas em branco nas pontas de cada payload.
    limpos: list[tuple[str, str, list[str]]] = []
    for sec, verbo, payload in diretivas:
        limpos.append((sec, verbo, _corpo_limpo(payload)))
    return limpos


def _chave_da_linha(linha: str) -> str | None:
    """Para 'atualizar': a chave de um item 'Key: value' (ou '- Key: value')."""
    texto = linha.lstrip("-*").strip()
    if ":" in texto:
        return _normalizar(texto.split(":", 1)[0])
    return None


def _aplicar_verbo(
    secao_nome: str, verbo: str, payload: list[str], corpo: list[str], avisos: list[str]
) -> list[str]:
    """Aplica um verbo ao corpo de uma seção. Retorna o novo corpo."""
    miolo = _corpo_limpo(corpo)

    if verbo == "substituir":
        return payload

    if verbo == "adicionar":
        existentes = {l.strip() for l in miolo}
        novos = [l for l in payload if l.strip() and l.strip() not in existentes]
        return miolo + novos

    if verbo == "remover":
        alvo = {l.strip() for l in payload if l.strip()}
        return [l for l in miolo if l.strip() not in alvo]

    if verbo == "atualizar":
        # Atualização campo a campo. Quebra o payload em itens; itens com
        # 'Key: value' substituem a linha de mesma chave (ou são adicionados).
        itens: list[str] = []
        for linha in payload:
            # 'a | b | c' vira três itens (formato inline de algumas personas).
            partes = [p for p in re.split(r"\s+\|\s+", linha) if p.strip()]
            itens.extend(partes if partes else [linha])
        resultado = list(miolo)
        for item in itens:
            chave = _chave_da_linha(item)
            valor = item.strip()
            if not valor.startswith(("-", "*")):
                valor = f"- {valor}"
            if chave is None:
                avisos.append(
                    f"[{secao_nome}] item sem 'Chave: valor' não mapeado em "
                    f"'atualizar': {item.strip()!r} (revise à mão)"
                )
                continue
            casou = False
            for idx, linha in enumerate(resultado):
                if _chave_da_linha(linha) == chave:
                    resultado[idx] = valor
                    casou = True
                    break
            if not casou:
                resultado.append(valor)
                avisos.append(
                    f"[{secao_nome}] campo sem correspondência adicionado em vez de "
                    f"substituído: {valor.strip()!r} (confira o diff)"
                )
        return resultado

    avisos.append(f"[{secao_nome}] verbo desconhecido: {verbo}")
    return miolo


def merge_update(alvo: Path, corpo_update: list[str]) -> tuple[str, list[str]]:
    """
    Aplica um bloco UPDATE ao arquivo alvo, seção a seção. Retorna
    (novo_conteúdo, avisos).
    """
    avisos: list[str] = []
    if not alvo.exists():
        raise FileNotFoundError(
            f"alvo do UPDATE não existe: {_rel(alvo)} — crie o arquivo base primeiro"
        )

    linhas = alvo.read_text(encoding="utf-8").splitlines()
    preambulo, secoes = _fatiar_secoes(linhas)
    indice = {_normalizar(_nome_secao(h)): i for i, (h, _) in enumerate(secoes)}

    for sec, verbo, payload in _parsear_diretivas(corpo_update):
        chave = _normalizar(sec)
        if chave not in indice:
            avisos.append(
                f"seção '{sec}' não encontrada em {_rel(alvo)} — diretiva ignorada"
            )
            continue
        i = indice[chave]
        header, corpo = secoes[i]
        novo_corpo = _aplicar_verbo(sec, verbo, payload, corpo, avisos)
        secoes[i] = (header, novo_corpo)

    # Reconstrói o arquivo, com uma linha em branco cercando cada seção.
    saida: list[str] = list(preambulo)
    if saida and saida[-1].strip():
        saida.append("")
    for header, corpo in secoes:
        saida.append(header)
        saida.append("")
        saida.extend(_corpo_limpo(corpo))
        saida.append("")
    texto = "\n".join(saida).rstrip("\n") + "\n"
    return texto, avisos


# ----------------------------------------------------------------------
# Diff / IO
# ----------------------------------------------------------------------

def _rel(p: Path) -> str:
    try:
        return p.relative_to(RAIZ_REPO).as_posix()
    except ValueError:
        return p.as_posix()


def _alvo_md_seguro(nome: str) -> Path | None:
    """Resolve o alvo .md sob a raiz do repo. None se o path escaparia da raiz."""
    p = (RAIZ_REPO / nome).resolve()
    try:
        p.relative_to(RAIZ_REPO.resolve())
    except ValueError:
        return None
    return p


def _diff(antigo: str, novo: str, alvo: str, limite: int = 40) -> list[str]:
    linhas = list(
        difflib.unified_diff(
            antigo.splitlines(),
            novo.splitlines(),
            fromfile=f"a/{alvo}",
            tofile=f"b/{alvo}",
            lineterm="",
        )
    )
    if len(linhas) > limite:
        linhas = linhas[:limite] + [f"... (+{len(linhas) - limite} linhas de diff)"]
    return linhas


# ----------------------------------------------------------------------
# Orquestração
# ----------------------------------------------------------------------

def planejar(texto: str, *, com_h1: bool = True) -> list[Acao]:
    """Calcula as ações (sem gravar nada)."""
    acoes: list[Acao] = []
    for bloco in extrair_blocos(texto):
        tipo = classificar(bloco.nome)

        if tipo == "codigo":
            acoes.append(
                Acao("ignora-código", bloco.nome, avisos=["crie à mão (fora do escopo)"])
            )
            continue
        if tipo == "ignora":
            acoes.append(Acao("ignora", bloco.nome, avisos=["marcador não-arquivo"]))
            continue

        if tipo == "md":
            alvo = _alvo_md_seguro(bloco.nome)
            if alvo is None:
                acoes.append(
                    Acao("ignora", bloco.nome, avisos=["alvo fora da raiz do repo — recusado"])
                )
                continue
            novo = montar_md(bloco.nome, bloco.corpo, com_h1=com_h1)
            antigo = alvo.read_text(encoding="utf-8") if alvo.exists() else ""
            if not alvo.exists():
                rotulo = "novo"
            elif antigo == novo:
                rotulo = "inalterado"
            else:
                rotulo = "sobrescreve"
            acoes.append(Acao(rotulo, _rel(alvo), diff=_diff(antigo, novo, _rel(alvo))))
            continue

        # tipo == update_state | update_project
        alvo = ALVO_STATE if tipo == "update_state" else ALVO_PROJECT
        try:
            novo, avisos = merge_update(alvo, bloco.corpo)
        except FileNotFoundError as exc:
            acoes.append(Acao("erro", bloco.nome, avisos=[str(exc)]))
            continue
        antigo = alvo.read_text(encoding="utf-8")
        rotulo = "inalterado" if antigo == novo else "merge"
        acoes.append(
            Acao(rotulo, _rel(alvo), diff=_diff(antigo, novo, _rel(alvo)), avisos=avisos)
        )
    return acoes


def executar(texto: str, *, com_h1: bool = True) -> list[Acao]:
    """Calcula e GRAVA as ações. Retorna as ações executadas."""
    acoes = planejar(texto, com_h1=com_h1)
    for bloco in extrair_blocos(texto):
        tipo = classificar(bloco.nome)
        if tipo == "md":
            alvo = _alvo_md_seguro(bloco.nome)
            if alvo is None:
                continue
            conteudo = montar_md(bloco.nome, bloco.corpo, com_h1=com_h1)
            if not alvo.exists() or alvo.read_text(encoding="utf-8") != conteudo:
                alvo.parent.mkdir(parents=True, exist_ok=True)
                alvo.write_text(conteudo, encoding="utf-8")
        elif tipo in ("update_state", "update_project"):
            alvo = ALVO_STATE if tipo == "update_state" else ALVO_PROJECT
            try:
                conteudo, _ = merge_update(alvo, bloco.corpo)
            except FileNotFoundError:
                continue
            if alvo.read_text(encoding="utf-8") != conteudo:
                alvo.write_text(conteudo, encoding="utf-8")
    return acoes


# ----------------------------------------------------------------------
# Fonte do texto (llm_output.md ou clipboard)
# ----------------------------------------------------------------------

def _ler_clipboard() -> str:
    if sys.platform == "win32":
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", "Get-Clipboard -Raw"],
            capture_output=True, text=True, encoding="utf-8",
        )
        if r.returncode == 0:
            return r.stdout
        raise RuntimeError(f"falha ao ler o clipboard: {r.stderr.strip()}")
    if sys.platform == "darwin":
        return subprocess.run(
            ["pbpaste"], capture_output=True, text=True, encoding="utf-8"
        ).stdout
    for cmd in (["xclip", "-selection", "clipboard", "-o"], ["xsel", "-b", "-o"]):
        try:
            return subprocess.run(
                cmd, capture_output=True, text=True, encoding="utf-8"
            ).stdout
        except FileNotFoundError:
            continue
    raise RuntimeError("clipboard não suportado neste SO (instale xclip ou xsel)")


def ler_fonte() -> tuple[str, Path | None]:
    """
    Híbrido: se llm_output.md tem marcadores, usa ele (origem = o path).
    Senão, lê do clipboard (origem = None).
    """
    if ARQUIVO_LLM_OUTPUT.exists():
        texto = ARQUIVO_LLM_OUTPUT.read_text(encoding="utf-8")
        if _tem_marcador(texto):
            return texto, ARQUIVO_LLM_OUTPUT
    return _ler_clipboard(), None


def zerar_llm_output() -> None:
    ARQUIVO_LLM_OUTPUT.write_text(TEMPLATE_LLM_OUTPUT, encoding="utf-8")


# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------

def _imprimir(acoes: list[Acao], *, write: bool, mostrar_diff: bool) -> None:
    icones = {
        "novo": "[novo]      ",
        "sobrescreve": "[sobrescreve]",
        "inalterado": "[inalterado]",
        "merge": "[merge]     ",
        "ignora-código": "[ignora-cod]",
        "ignora": "[ignora]    ",
        "erro": "[ERRO]      ",
    }
    if not acoes:
        print("[copiloto] nenhum bloco <!-- INICIO: ... --> encontrado na fonte.")
        return
    for a in acoes:
        print(f"  {icones.get(a.rotulo, a.rotulo)} {a.alvo}")
        for av in a.avisos:
            print(f"      ! {av}")
        if mostrar_diff and a.diff:
            for linha in a.diff:
                print(f"      {linha}")
    grava = [a for a in acoes if a.rotulo in ("novo", "sobrescreve", "merge")]
    if write:
        print(f"[copiloto] {len(grava)} arquivo(s) gravado(s).")
    else:
        print(
            f"[copiloto] dry-run: {len(grava)} arquivo(s) seriam gravados. "
            "Rode de novo com --write pra aplicar."
        )


def main_aplicar(args) -> int:
    com_h1 = not args.sem_h1
    try:
        texto, origem = ler_fonte()
    except Exception as exc:  # noqa: BLE001
        print(f"[copiloto] ERRO: {exc}", file=sys.stderr)
        return 1

    fonte_nome = _rel(origem) if origem else "clipboard"
    print(f"[copiloto] fonte: {fonte_nome}")

    if args.write:
        acoes = executar(texto, com_h1=com_h1)
        _imprimir(acoes, write=True, mostrar_diff=args.diff)
        # Zera o llm_output.md só se foi a fonte e algo foi gravado.
        gravou = any(a.rotulo in ("novo", "sobrescreve", "merge") for a in acoes)
        if origem is not None and gravou:
            zerar_llm_output()
            print(f"[copiloto] {fonte_nome} zerado pro próximo uso.")
    else:
        acoes = planejar(texto, com_h1=com_h1)
        _imprimir(acoes, write=False, mostrar_diff=True)
    return 0
