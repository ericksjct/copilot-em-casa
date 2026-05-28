"""
Análise de schemas de DataFrames via registry explícito.

Refator do schema_dump.py original. A API agora é um registry: o usuário
registra DataFrames conforme cria, e a geração da seção lê o registry.

Uso típico no main.py:

    from scripts.gsd import registry, snapshot_completo

    df_balancete = carregar_balancete()
    registry.add("balancete", df_balancete)

    df_cop = processar_cop(df_balancete)
    registry.add("cop", df_cop)

    # ... no fim do pipeline ...
    snapshot_completo()
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pandas as pd

if TYPE_CHECKING:
    import polars as pl

try:
    import polars as pl  # type: ignore[import-not-found,no-redef]
    HAS_POLARS = True
except ImportError:
    HAS_POLARS = False
    pl = None  # type: ignore[assignment]


# Limite de caracteres por célula nas amostras (trunca com '...' no fim).
# Evita que colunas como "histórico contábil" estourem o .txt.
MAX_LEN_CELULA = 50
N_LINHAS_AMOSTRA = 3


class DataFrameRegistry:
    """
    Registro explícito de DataFrames a serem dumpados na seção SCHEMAS.

    Singleton instanciado no nível do módulo (ver `registry` abaixo).
    Não é thread-safe — o pipeline é single-thread.
    """

    def __init__(self) -> None:
        self._entradas: dict[str, Any] = {}

    def add(self, nome: str, df: Any) -> None:
        """
        Registra um DataFrame com nome canônico.

        Args:
            nome: nome que aparecerá no snapshot. Convenção: snake_case,
                sem prefixo 'df_' (use 'balancete', não 'df_balancete').
            df: pandas.DataFrame, polars.DataFrame, ou None (vira AUSENTE).

        Sobrescreve silenciosamente se o nome já existir — útil quando o
        DataFrame é reatribuído ao longo do pipeline.
        """
        if not nome or not isinstance(nome, str):
            raise ValueError(f"nome deve ser string não-vazia (recebido: {nome!r})")
        self._entradas[nome] = df

    def clear(self) -> None:
        """Esvazia o registry. Útil em testes."""
        self._entradas.clear()

    def items(self) -> list[tuple[str, Any]]:
        """Retorna lista de (nome, df) na ordem de inserção."""
        return list(self._entradas.items())

    def __len__(self) -> int:
        return len(self._entradas)

    def __contains__(self, nome: str) -> bool:
        return nome in self._entradas


# Singleton exposto pelo __init__.py
registry = DataFrameRegistry()


def gerar_secao_schemas() -> list[str]:
    """
    Gera as linhas da seção SCHEMAS do snapshot a partir do registry.

    Returns:
        Lista de linhas. Se o registry estiver vazio, retorna nota
        explicativa em vez de seção vazia.
    """
    if len(registry) == 0:
        return [
            "[schemas não disponíveis — registry vazio]",
            "",
            "Pra popular esta seção, registre os DataFrames no main.py:",
            "",
            "    from scripts.gsd import registry",
            "    registry.add('balancete', df_balancete)",
            "    registry.add('cop', df_cop)",
            "",
            "E chame snapshot_completo() ao final do pipeline.",
        ]

    linhas: list[str] = []
    validos = 0
    ausentes: list[str] = []
    invalidos: list[tuple[str, str]] = []

    for nome, df in registry.items():
        if df is None:
            linhas.append(f"### {nome}")
            linhas.append("  [AUSENTE] Variável é None — não gerado nesta execução")
            linhas.append("")
            ausentes.append(nome)
            continue

        bloco = _formatar_schema(nome, df)
        if bloco is None:
            tipo = type(df).__name__
            linhas.append(f"### {nome}")
            linhas.append(f"  [INVÁLIDO] Tipo não suportado: {tipo}")
            linhas.append("             Esperado: pandas.DataFrame ou polars.DataFrame")
            linhas.append("")
            invalidos.append((nome, tipo))
            continue

        linhas.append(bloco)
        linhas.append("")
        validos += 1

    # Sumário ao final
    linhas.append("-" * 70)
    linhas.append("Resumo da seção:")
    linhas.append(f"  Válidos:   {validos}")
    linhas.append(f"  Ausentes:  {len(ausentes)}")
    linhas.append(f"  Inválidos: {len(invalidos)}")

    if ausentes:
        linhas.append("")
        linhas.append("Ausentes (None):")
        for n in ausentes:
            linhas.append(f"  - {n}")

    if invalidos:
        linhas.append("")
        linhas.append("Inválidos (tipo errado):")
        for n, t in invalidos:
            linhas.append(f"  - {n} ({t})")

    return linhas


def _formatar_schema(nome: str, df: Any) -> str | None:
    """Formata schema de um DataFrame. Retorna None se não for DataFrame."""
    if isinstance(df, pd.DataFrame):
        return _formatar_pandas(nome, df)
    if HAS_POLARS and isinstance(df, pl.DataFrame):  # type: ignore[union-attr]
        return _formatar_polars(nome, df)
    return None


def _formatar_pandas(nome: str, df: pd.DataFrame) -> str:
    linhas = []
    linhas.append(f"### {nome}")
    linhas.append("Engine: pandas")
    linhas.append(f"Shape: {df.shape[0]:,} linhas × {df.shape[1]} colunas")
    if df.index.name:
        linhas.append(f"Index: {df.index.name} ({df.index.dtype})")
    linhas.append("")
    linhas.append("Colunas (dtypes):")

    if df.columns.empty:
        linhas.append("  (nenhuma coluna)")
        return "\n".join(linhas)

    max_col = max(len(str(c)) for c in df.columns)

    for col, dtype in df.dtypes.items():
        nulls = df[col].isna().sum()
        null_pct = (nulls / len(df) * 100) if len(df) > 0 else 0
        null_info = f"  ({nulls:,} nulls, {null_pct:.1f}%)" if nulls > 0 else ""
        linhas.append(f"  {str(col).ljust(max_col)}  {dtype}{null_info}")

    return "\n".join(linhas)


def _formatar_polars(nome: str, df: pl.DataFrame) -> str:
    linhas = []
    linhas.append(f"### {nome}")
    linhas.append("Engine: polars")
    linhas.append(f"Shape: {df.height:,} linhas × {df.width} colunas")
    linhas.append("")
    linhas.append("Colunas (dtypes):")

    if df.width == 0:
        linhas.append("  (nenhuma coluna)")
        return "\n".join(linhas)

    max_col = max(len(str(c)) for c in df.columns)

    for col, dtype in df.schema.items():
        nulls = df[col].null_count()
        null_pct = (nulls / df.height * 100) if df.height > 0 else 0
        null_info = f"  ({nulls:,} nulls, {null_pct:.1f}%)" if nulls > 0 else ""
        linhas.append(f"  {str(col).ljust(max_col)}  {dtype}{null_info}")

    return "\n".join(linhas)


# ----------------------------------------------------------------------
# Variantes com amostra (uso exclusivo do snapshot_architect)
# ----------------------------------------------------------------------

def gerar_secao_schemas_com_amostra(
    nomes: list[str] | None = None,
) -> list[str]:
    """
    Versão de gerar_secao_schemas() que inclui 3 linhas de amostra real
    por DataFrame. ATENÇÃO: pode conter PII. Saída deve ficar local
    (.temp/architect-snapshot.txt), nunca em chat externo.

    Args:
        nomes: lista de nomes do registry a incluir. Se None (default),
            inclui todos. Se algum nome não existir no registry, levanta
            KeyError listando os nomes disponíveis.

    Returns:
        Lista de linhas. Se o registry estiver vazio (ou o filtro resultar
        em conjunto vazio), retorna nota explicativa.
    """
    if len(registry) == 0:
        return [
            "[schemas não disponíveis — registry vazio]",
            "",
            "Pra popular esta seção, registre os DataFrames no main.py:",
            "",
            "    from scripts.gsd import registry",
            "    registry.add('balancete', df_balancete)",
            "",
            "E chame snapshot_architect() ao final do pipeline.",
        ]

    # Filtra registry pelos nomes pedidos
    entradas_disponiveis = dict(registry.items())

    if nomes is None:
        entradas_filtradas = list(entradas_disponiveis.items())
    else:
        nomes_invalidos = [n for n in nomes if n not in entradas_disponiveis]
        if nomes_invalidos:
            disponiveis = sorted(entradas_disponiveis.keys())
            raise KeyError(
                f"Nome(s) não encontrado(s) no registry: {nomes_invalidos}. "
                f"Disponíveis: {disponiveis}"
            )
        # Preserva a ordem pedida pelo usuário, não a do registry
        entradas_filtradas = [(n, entradas_disponiveis[n]) for n in nomes]

    linhas: list[str] = []
    linhas.append("AVISO: este arquivo contém amostras reais dos DataFrames.")
    linhas.append("Pode incluir dados sensíveis (PII, valores financeiros).")
    linhas.append("Mantenha local. Não cole em chat externo nem commite.")
    linhas.append("")

    if nomes is not None:
        linhas.append(f"Filtro aplicado: {nomes}")
        linhas.append("")

    for nome, df in entradas_filtradas:
        if df is None:
            linhas.append(f"### {nome}")
            linhas.append("  [AUSENTE] Variável é None")
            linhas.append("")
            continue

        bloco = _formatar_schema_com_amostra(nome, df)
        if bloco is None:
            tipo = type(df).__name__
            linhas.append(f"### {nome}")
            linhas.append(f"  [INVÁLIDO] Tipo não suportado: {tipo}")
            linhas.append("")
            continue

        linhas.append(bloco)
        linhas.append("")

    return linhas


def _formatar_schema_com_amostra(nome: str, df: Any) -> str | None:
    """Mesma lógica de _formatar_schema, mas inclui amostra."""
    if isinstance(df, pd.DataFrame):
        return _formatar_pandas_com_amostra(nome, df)
    if HAS_POLARS and isinstance(df, pl.DataFrame):  # type: ignore[union-attr]
        return _formatar_polars_com_amostra(nome, df)
    return None


def _truncar(valor: Any) -> str:
    """Converte valor pra string e trunca em MAX_LEN_CELULA caracteres."""
    s = str(valor)
    if len(s) > MAX_LEN_CELULA:
        return s[: MAX_LEN_CELULA - 3] + "..."
    return s


def _formatar_pandas_com_amostra(nome: str, df: pd.DataFrame) -> str:
    # Reusa o cabeçalho de schema padrão
    cabecalho = _formatar_pandas(nome, df)
    linhas = [cabecalho, ""]

    if len(df) == 0:
        linhas.append("Amostra: (DataFrame vazio)")
        return "\n".join(linhas)

    linhas.append(f"Amostra (primeiras {N_LINHAS_AMOSTRA} linhas):")

    amostra = df.head(N_LINHAS_AMOSTRA)
    # Aplica truncamento célula a célula via applymap (pandas) / map (pandas >= 2.1)
    try:
        amostra_truncada = amostra.map(_truncar)  # pandas >= 2.1
    except AttributeError:
        amostra_truncada = amostra.applymap(_truncar)  # pandas < 2.1

    # to_string com largura controlada
    texto = amostra_truncada.to_string(
        index=False,
        max_cols=None,
        max_colwidth=MAX_LEN_CELULA,
    )
    for linha in texto.split("\n"):
        linhas.append(f"  {linha}")

    return "\n".join(linhas)


def _formatar_polars_com_amostra(nome: str, df: pl.DataFrame) -> str:
    cabecalho = _formatar_polars(nome, df)
    linhas = [cabecalho, ""]

    if df.height == 0:
        linhas.append("Amostra: (DataFrame vazio)")
        return "\n".join(linhas)

    linhas.append(f"Amostra (primeiras {N_LINHAS_AMOSTRA} linhas):")

    # Polars: converte amostra para Python e trunca manualmente.
    # Evita depender do __repr__ default do polars (que tem largura própria).
    amostra = df.head(N_LINHAS_AMOSTRA)
    colunas = amostra.columns
    linhas_dict = amostra.to_dicts()

    # Calcula largura por coluna (truncando os valores antes)
    larguras = {col: len(col) for col in colunas}
    valores_truncados: list[dict[str, str]] = []
    for linha_dict in linhas_dict:
        linha_truncada = {col: _truncar(linha_dict[col]) for col in colunas}
        valores_truncados.append(linha_truncada)
        for col in colunas:
            larguras[col] = max(larguras[col], len(linha_truncada[col]))

    # Renderiza header
    header = "  ".join(col.ljust(larguras[col]) for col in colunas)
    linhas.append(f"  {header}")
    linhas.append(f"  {'  '.join('-' * larguras[col] for col in colunas)}")

    # Renderiza linhas
    for linha_truncada in valores_truncados:
        linha_render = "  ".join(
            linha_truncada[col].ljust(larguras[col]) for col in colunas
        )
        linhas.append(f"  {linha_render}")

    return "\n".join(linhas)
