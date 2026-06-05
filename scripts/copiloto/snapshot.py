"""
Orquestração do snapshot unificado.

Concatena árvore, assinaturas e schemas (se disponíveis) num único .txt
em .temp/codebase-snapshot.txt.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from scripts.copiloto.paths import ARQUIVO_AMOSTRAS, ARQUIVO_SNAPSHOT, garantir_temp

SEPARADOR = "=" * 70


def _cabecalho_secao(titulo: str) -> list[str]:
    """Bloco de cabeçalho grosso para uma seção do snapshot."""
    return [SEPARADOR, titulo, SEPARADOR, ""]


def _cabecalho_global() -> list[str]:
    """Cabeçalho do arquivo todo: título + timestamp."""
    agora = datetime.now().isoformat(timespec="seconds")
    return [
        SEPARADOR,
        "CODEBASE SNAPSHOT",
        f"Gerado em: {agora}",
        SEPARADOR,
        "",
    ]


def snapshot_completo(
    *,
    incluir_schemas: bool = True,
    destino: Path | None = None,
) -> Path:
    """
    Gera o snapshot unificado em .temp/codebase-snapshot.txt.

    Args:
        incluir_schemas: se True, inclui a seção de schemas a partir do
            registry. Se o registry estiver vazio, a seção sai com nota
            "schemas não disponíveis — rode o pipeline".
        destino: path customizado de saída. Padrão: .temp/codebase-snapshot.txt
            na raiz do repo.

    Returns:
        Path do arquivo gerado.
    """
    # Imports tardios: arvore/assinaturas não tocam pandas/polars,
    # mas schemas sim. Mantém o import do __init__ leve.
    from scripts.copiloto.arvore import gerar_arvore
    from scripts.copiloto.assinaturas import gerar_assinaturas
    from scripts.copiloto.schemas import gerar_secao_schemas

    garantir_temp()
    saida = destino or ARQUIVO_SNAPSHOT

    linhas: list[str] = []
    linhas.extend(_cabecalho_global())

    # Seção 1: árvore
    linhas.extend(_cabecalho_secao("ÁRVORE"))
    linhas.extend(gerar_arvore())
    linhas.append("")

    # Seção 2: assinaturas
    linhas.extend(_cabecalho_secao("ASSINATURAS"))
    linhas.extend(gerar_assinaturas())
    linhas.append("")

    # Seção 3: schemas (condicional)
    linhas.extend(_cabecalho_secao("SCHEMAS"))
    if incluir_schemas:
        linhas.extend(gerar_secao_schemas())
    else:
        linhas.append("[seção omitida — incluir_schemas=False]")
    linhas.append("")

    saida.write_text("\n".join(linhas), encoding="utf-8")

    print(f"[copiloto] snapshot gerado em: {saida}")
    return saida


def snapshot_amostras(
    *,
    nomes: list[str] | None = None,
    destino: Path | None = None,
) -> Path:
    """
    Gera o snapshot extendido com amostras reais dos DataFrames, em
    .temp/amostras-snapshot.txt.

    Diferença para snapshot_completo():
        - Apenas a seção SCHEMAS (sem árvore, sem assinaturas).
        - Cada DataFrame inclui 3 linhas de amostra REAL (head(3)).
        - Aviso explícito no topo sobre PII / dados sensíveis.

    Args:
        nomes: lista de DataFrames a incluir. Se None (default), inclui
            todos do registry. Se passar nome inválido, levanta KeyError
            listando os disponíveis.
        destino: path customizado de saída. Padrão:
            .temp/amostras-snapshot.txt na raiz do repo.

    Returns:
        Path do arquivo gerado.

    Atenção:
        O arquivo gerado pode conter dados sensíveis (CPF/CNPJ, saldos,
        valores contábeis). Mantenha-o local. Não cole em chat externo.
        Não commite no Git (.temp/ deve estar gitignored).
    """
    from scripts.copiloto.schemas import gerar_secao_schemas_com_amostra

    garantir_temp()
    saida = destino or ARQUIVO_AMOSTRAS

    linhas: list[str] = []
    linhas.extend(_cabecalho_global())

    titulo_secao = "SCHEMAS (com amostras reais)"
    if nomes is not None:
        titulo_secao += f" — filtro: {', '.join(nomes)}"

    linhas.extend(_cabecalho_secao(titulo_secao))
    linhas.extend(gerar_secao_schemas_com_amostra(nomes=nomes))
    linhas.append("")

    saida.write_text("\n".join(linhas), encoding="utf-8")

    print(f"[copiloto] snapshot de amostras gerado em: {saida}")
    print("[copiloto] AVISO: arquivo contém amostras reais. Mantenha local.")
    return saida
