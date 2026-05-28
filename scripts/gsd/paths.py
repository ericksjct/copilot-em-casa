"""Constantes de path compartilhadas pelo pacote scripts.gsd."""
from __future__ import annotations

from pathlib import Path


def _achar_raiz_repo() -> Path:
    """Sobe na árvore de diretórios até achar .git ou estourar."""
    atual = Path(__file__).resolve()
    for parent in [atual, *atual.parents]:
        if (parent / ".git").exists():
            return parent
    raise RuntimeError(
        "Raiz do repositório não encontrada (nenhum .git/ subindo de "
        f"{atual}). Rode de dentro de um repo Git."
    )


RAIZ_REPO: Path = _achar_raiz_repo()
DIR_TEMP: Path = RAIZ_REPO / ".temp"
ARQUIVO_SNAPSHOT: Path = DIR_TEMP / "codebase-snapshot.txt"
ARQUIVO_ARCHITECT: Path = DIR_TEMP / "architect-snapshot.txt"


def garantir_temp() -> Path:
    """Garante que .temp/ existe na raiz do repo. Retorna o path."""
    DIR_TEMP.mkdir(parents=True, exist_ok=True)
    return DIR_TEMP
