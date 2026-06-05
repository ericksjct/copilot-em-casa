"""
Geração da árvore de arquivos do projeto.

Porta Python do gerar-arvore.ps1. Usa `git ls-files` via subprocess pra
respeitar .gitignore automaticamente. Não importa pandas/polars.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from scripts.copiloto.paths import RAIZ_REPO

PROFUNDIDADE_PADRAO = 3


def _git_ls_files() -> list[str]:
    """Lista arquivos versionados via git ls-files. Roda na raiz do repo."""
    resultado = subprocess.run(
        ["git", "ls-files"],
        cwd=RAIZ_REPO,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if resultado.returncode != 0:
        raise RuntimeError(
            f"git ls-files falhou (exit {resultado.returncode}): "
            f"{resultado.stderr.strip()}"
        )

    arquivos = [
        linha.strip()
        for linha in resultado.stdout.splitlines()
        if linha.strip()
    ]
    return arquivos


def gerar_arvore(
    *,
    profundidade: int = PROFUNDIDADE_PADRAO,
    incluir_arquivos: bool = True,
) -> list[str]:
    """
    Gera a árvore hierárquica do projeto como lista de linhas.

    Args:
        profundidade: profundidade máxima a exibir (>= 1).
        incluir_arquivos: se True, lista arquivos. Se False, só pastas.

    Returns:
        Lista de linhas (sem '\\n' no fim) prontas pra serem juntadas.
        Primeira linha é sempre '.'.
    """
    if profundidade < 1:
        raise ValueError(f"profundidade deve ser >= 1 (recebido: {profundidade})")

    arquivos = _git_ls_files()
    if not arquivos:
        return [".", "[repositório vazio ou sem arquivos versionados]"]

    # Constrói conjunto ordenado de pastas + arquivos
    entradas: set[str] = set()
    for arquivo in arquivos:
        partes = arquivo.split("/")

        # Adiciona cada nível de pasta até a profundidade-1
        # (pastas terminam com '/')
        limite_pastas = min(len(partes) - 1, profundidade)
        for i in range(limite_pastas):
            pasta = "/".join(partes[: i + 1]) + "/"
            entradas.add(pasta)

        # Adiciona o arquivo se couber na profundidade
        if incluir_arquivos and len(partes) <= profundidade:
            entradas.add(arquivo)

    # Ordena: pastas e arquivos misturados, ordem alfabética estável
    ordenados = sorted(entradas)

    # Formata com indentação por profundidade
    linhas = ["."]
    for item in ordenados:
        eh_pasta = item.endswith("/")
        partes = item.rstrip("/").split("/")
        depth = len(partes) - 1
        indent = "  " * depth
        nome = partes[-1] + ("/" if eh_pasta else "")
        linhas.append(f"{indent}{nome}")

    return linhas
