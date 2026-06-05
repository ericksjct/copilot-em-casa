"""
Extração de assinaturas de funções e classes do projeto.

Porta Python do gerar-assinaturas.ps1. Usa `git grep` via subprocess pra
respeitar .gitignore automaticamente. Não importa pandas/polars.
"""
from __future__ import annotations

import subprocess
from typing import Literal

from scripts.copiloto.paths import RAIZ_REPO

Linguagem = Literal["python", "sql"]

# Padrões de busca por linguagem
PADROES: dict[Linguagem, dict[str, str]] = {
    "python": {
        "regex": r"^(def |class |async def )",
        "extensao": "*.py",
    },
    "sql": {
        "regex": r"^(CREATE|create) (TABLE|VIEW|FUNCTION|PROCEDURE|table|view|function|procedure)",
        "extensao": "*.sql",
    },
}


def _git_grep(regex: str, extensao: str) -> list[str]:
    """
    Roda git grep com o padrão na extensão indicada. Retorna lista de
    linhas no formato 'path:linha:conteúdo'.
    """
    resultado = subprocess.run(
        ["git", "grep", "-n", "-E", regex, "--", extensao],
        cwd=RAIZ_REPO,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    # git grep retorna exit 1 quando não acha nada — isso é "OK, vazio",
    # não erro. Só tratamos como erro se for >= 2.
    if resultado.returncode >= 2:
        raise RuntimeError(
            f"git grep falhou (exit {resultado.returncode}): "
            f"{resultado.stderr.strip()}"
        )

    return [
        linha.strip()
        for linha in resultado.stdout.splitlines()
        if linha.strip()
    ]


def _formatar_linha(linha_grep: str) -> str:
    """
    Converte saída do git grep ('path:N:conteúdo') no formato canônico
    'path:N: conteúdo' (com espaço após o segundo ':' e conteúdo strip).

    Se a linha não bater o padrão esperado, retorna como veio.
    """
    partes = linha_grep.split(":", 2)
    if len(partes) != 3:
        return linha_grep

    path, num_linha, conteudo = partes
    return f"{path}:{num_linha}: {conteudo.strip()}"


def gerar_assinaturas(
    *,
    linguagem: Linguagem = "python",
) -> list[str]:
    """
    Extrai assinaturas de funções e classes do projeto.

    Args:
        linguagem: 'python' (def/class/async def) ou 'sql' (CREATE TABLE/
            VIEW/FUNCTION/PROCEDURE).

    Returns:
        Lista de linhas no formato 'path:linha: assinatura'. Vazia se
        nenhuma assinatura for encontrada.
    """
    if linguagem not in PADROES:
        raise ValueError(
            f"Linguagem '{linguagem}' não suportada. "
            f"Opções: {list(PADROES.keys())}"
        )

    config = PADROES[linguagem]
    linhas_raw = _git_grep(config["regex"], config["extensao"])

    if not linhas_raw:
        return [f"[nenhuma assinatura encontrada para linguagem={linguagem}]"]

    return [_formatar_linha(linha) for linha in linhas_raw]
