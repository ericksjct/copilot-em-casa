"""
Empacotador de arquivos sob demanda: python -m scripts.copiloto pack <path> ...

Lê arquivos (ou todos os arquivos de texto de uma pasta, recursivo), embrulha
cada um no separador `=== ARQUIVO: path ===` e escreve em .temp/pack.txt,
ecoando na stdout pra você colar direto do terminal no chat.

É a contrapartida do modelo "você é o runtime": em vez da persona pedir
"cole main.py, cole conciliacao.py", ela emite o comando e você cola a saída.
    python -m scripts.copiloto pack src/orquestrador.py src/conciliacao/
"""
from __future__ import annotations

from pathlib import Path

from scripts.copiloto.paths import DIR_TEMP, RAIZ_REPO, garantir_temp

ARQUIVO_PACK: Path = DIR_TEMP / "pack.txt"

# Extensões de texto que faz sentido empacotar ao varrer uma pasta.
EXTS_TEXTO: frozenset[str] = frozenset(
    {".py", ".sql", ".toml", ".yaml", ".yml", ".cfg", ".ini", ".md", ".txt", ".json"}
)

# Pastas que nunca varremos ao expandir um diretório.
IGNORAR_DIRS: frozenset[str] = frozenset(
    {
        ".git",
        ".temp",
        "__pycache__",
        ".venv",
        "venv",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        "node_modules",
    }
)


def _resolver_alvos(paths: list[str]) -> list[Path]:
    """
    Expande cada path: arquivo vira ele mesmo; pasta vira os arquivos de texto
    dentro dela (recursivo, ignorando IGNORAR_DIRS). Mantém a ordem dada,
    deduplicando.
    """
    alvos: list[Path] = []
    for p in paths:
        bruto = Path(p)
        alvo = bruto if bruto.is_absolute() else (RAIZ_REPO / bruto)
        if alvo.is_dir():
            for filho in sorted(alvo.rglob("*")):
                if not filho.is_file() or filho.suffix not in EXTS_TEXTO:
                    continue
                if any(parte in IGNORAR_DIRS for parte in filho.parts):
                    continue
                alvos.append(filho)
        elif alvo.is_file():
            alvos.append(alvo)
        else:
            raise FileNotFoundError(f"não encontrado: {p} (resolvido para {alvo})")

    vistos: set[Path] = set()
    unicos: list[Path] = []
    for a in alvos:
        if a not in vistos:
            vistos.add(a)
            unicos.append(a)
    return unicos


def _rel(path: Path) -> str:
    """Path relativo à raiz do repo, com barra normal, pro cabeçalho do bloco."""
    try:
        return path.relative_to(RAIZ_REPO).as_posix()
    except ValueError:
        return path.as_posix()


def empacotar(paths: list[str], *, destino: Path | None = None) -> str:
    """
    Empacota arquivos/pastas num único texto no formato `=== ARQUIVO: path ===`.

    Args:
        paths: arquivos ou pastas. Pasta é varrida recursivamente pelos
            arquivos de texto (.py, .sql, .yaml, ...).
        destino: saída. Padrão: .temp/pack.txt na raiz do repo.

    Returns:
        O conteúdo empacotado (também escrito em `destino`).

    Raises:
        ValueError: se `paths` vier vazio.
        FileNotFoundError: se um path não existir, ou se nenhuma pasta dada
            contiver arquivo de texto.
    """
    if not paths:
        raise ValueError("pack precisa de ao menos um arquivo ou pasta")

    alvos = _resolver_alvos(paths)
    if not alvos:
        raise FileNotFoundError("nenhum arquivo de texto encontrado nos paths dados")

    blocos: list[str] = []
    for alvo in alvos:
        rel = _rel(alvo)
        try:
            conteudo = alvo.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            blocos.append(f"=== ARQUIVO: {rel} ===\n[binário ou não-UTF-8 — pulado]\n")
            continue
        blocos.append(f"=== ARQUIVO: {rel} ===\n{conteudo.rstrip()}\n")

    texto = "\n".join(blocos)

    garantir_temp()
    saida = destino or ARQUIVO_PACK
    saida.write_text(texto, encoding="utf-8")
    return texto
