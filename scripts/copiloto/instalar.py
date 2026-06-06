"""
Instala o toolkit do Copilot em Casa num repo de trabalho:
python -m scripts.copiloto instalar [DESTINO] [--write]

O problema que isso resolve: colocar os arquivos nos lugares certos do projeto
era um trabalho artesanal (copiar de `templates/` E de `scripts/`, criar pastas,
editar o `.gitignore` à mão) — lento e fácil de errar a hierarquia. Aqui o
mapeamento origem->destino vira um manifesto declarativo (PAYLOAD) que o comando
executa; você nunca mais coloca arquivo no lugar à mão.

Por padrão roda em DRY-RUN: mostra a árvore exata que seria gravada. Use --write
pra gravar de fato.

    python -m scripts.copiloto instalar C:\\proj\\novo            # preview
    python -m scripts.copiloto instalar C:\\proj\\novo --write     # grava

Modos de cada entrada do PAYLOAD (resolvem o re-install num projeto que já usa o
toolkit):

  - "sempre"  -> sobrescreve sempre. Para o código do tool, o RULES.md e o
    manual: devem acompanhar a versão do toolkit.
  - "semente" -> só cria se faltar; nunca esmaga o que já existe. Para o estado
    vivo do projeto (PROJECT.md, STATE.md, planos, llm_output.md).

O `.gitignore` do destino é mesclado: as linhas que faltam são anexadas (snapshot,
pack, fixtures e a resposta colada da persona podem conter dado real).
"""
from __future__ import annotations

import argparse
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

# Raiz do toolkit (esta cópia do repo copilot-em-casa). Calculada a partir do
# próprio arquivo — não depende de .git, pra funcionar mesmo rodando de fora.
# copiloto -> scripts -> raiz do toolkit
RAIZ_TOOLKIT: Path = Path(__file__).resolve().parents[2]

# Pastas que nunca copiamos ao varrer uma árvore.
IGNORAR: frozenset[str] = frozenset(
    {".git", ".temp", "__pycache__", ".venv", "venv", ".mypy_cache",
     ".pytest_cache", ".ruff_cache", "node_modules"}
)

# ----------------------------------------------------------------------
# O manifesto: a fonte única da verdade da hierarquia de instalação.
# (origem relativa à raiz do toolkit, destino relativo à raiz do projeto, modo)
# ----------------------------------------------------------------------
PAYLOAD: tuple[tuple[str, str, str], ...] = (
    # Regras e referência: acompanham a versão do toolkit -> "sempre".
    ("templates/RULES.md",                  "RULES.md",                  "sempre"),
    ("templates/manual-copilot-windows.md", "manual-copilot-windows.md", "sempre"),
    # Buffer do `aplicar`: pode ter conteúdo colado -> "semente".
    ("templates/llm_output.md",             "llm_output.md",             "semente"),
    # Estado vivo do projeto: nunca esmagar -> "semente" (por arquivo da árvore).
    ("templates/docs/copiloto",             "docs/copiloto",             "semente"),
    # Código do tool: acompanha a versão do toolkit -> "sempre".
    ("scripts/copiloto",                    "scripts/copiloto",          "sempre"),
)

# Linhas que o `.gitignore` do destino precisa ter. Idempotente: só anexa as que
# faltarem. Snapshot/pack/fixtures e a resposta da persona podem conter dado real.
LINHAS_GITIGNORE: tuple[str, ...] = (
    ".temp/",
    "__pycache__/",
    "*.pyc",
    "tests/fixtures/",
    "/llm_output.md",
)
CABECALHO_GITIGNORE = "# copiloto em casa"


# ----------------------------------------------------------------------
# Planejamento (sem efeito colateral)
# ----------------------------------------------------------------------
@dataclass(frozen=True)
class Acao:
    """Uma operação de cópia planejada, com seu status pro preview."""
    origem: Path
    destino: Path
    rel: str          # destino relativo à raiz do projeto (pra exibir)
    status: str       # "criar" | "atualizar" | "pular (preserva existente)"


def _arquivos_da_arvore(raiz: Path) -> list[Path]:
    """Arquivos sob `raiz`, recursivo, ignorando IGNORAR. Ordenado."""
    return sorted(
        f for f in raiz.rglob("*")
        if f.is_file() and not any(parte in IGNORAR for parte in f.relative_to(raiz).parts)
    )


def _status(destino: Path, modo: str) -> str:
    if not destino.exists():
        return "criar"
    return "atualizar" if modo == "sempre" else "pular (preserva existente)"


def planejar(destino_raiz: Path) -> list[Acao]:
    """
    Resolve o PAYLOAD num plano de ações concretas (uma por arquivo), sem gravar.
    Levanta FileNotFoundError se uma origem do manifesto não existir no toolkit.
    """
    acoes: list[Acao] = []
    for origem_rel, destino_rel, modo in PAYLOAD:
        origem = RAIZ_TOOLKIT / origem_rel
        if not origem.exists():
            raise FileNotFoundError(
                f"origem do manifesto não existe no toolkit: {origem_rel} "
                f"(resolvido para {origem})"
            )

        if origem.is_dir():
            for arquivo in _arquivos_da_arvore(origem):
                sub = arquivo.relative_to(origem)
                dest = destino_raiz / destino_rel / sub
                rel = (Path(destino_rel) / sub).as_posix()
                acoes.append(Acao(arquivo, dest, rel, _status(dest, modo)))
        else:
            dest = destino_raiz / destino_rel
            acoes.append(Acao(origem, dest, destino_rel, _status(dest, modo)))
    return acoes


def planejar_gitignore(destino_raiz: Path) -> list[str]:
    """Retorna as linhas que faltam no .gitignore do destino (vazio = ok)."""
    alvo = destino_raiz / ".gitignore"
    existentes: set[str] = set()
    if alvo.exists():
        existentes = {ln.strip() for ln in alvo.read_text(encoding="utf-8").splitlines()}
    return [ln for ln in LINHAS_GITIGNORE if ln not in existentes]


# ----------------------------------------------------------------------
# Execução
# ----------------------------------------------------------------------
def _aplicar_acao(acao: Acao) -> None:
    if acao.status.startswith("pular"):
        return
    acao.destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(acao.origem, acao.destino)


def _aplicar_gitignore(destino_raiz: Path, faltantes: list[str]) -> None:
    if not faltantes:
        return
    alvo = destino_raiz / ".gitignore"
    atual = alvo.read_text(encoding="utf-8") if alvo.exists() else ""
    prefixo = "" if atual == "" or atual.endswith("\n") else "\n"
    bloco = "\n".join(faltantes)
    alvo.write_text(f"{atual}{prefixo}{CABECALHO_GITIGNORE}\n{bloco}\n", encoding="utf-8")


# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------
def _resolver_destino(arg: str | None) -> Path:
    destino = Path(arg).resolve() if arg else Path.cwd().resolve()
    if destino == RAIZ_TOOLKIT:
        raise ValueError(
            "destino e a propria raiz do toolkit - passe o caminho do projeto de "
            "trabalho: python -m scripts.copiloto instalar C:\\proj\\novo --write"
        )
    return destino


def _imprimir_plano(destino: Path, acoes: list[Acao], faltantes: list[str]) -> None:
    print(f"[copiloto] instalar em: {destino}\n")
    for a in acoes:
        marca = {"criar": "+", "atualizar": "~"}.get(a.status, " ")
        print(f"  {marca} {a.rel:<48} {a.status}")
    if faltantes:
        print(f"\n  .gitignore (anexar {len(faltantes)} linha(s)): {', '.join(faltantes)}")
    else:
        print("\n  .gitignore: já cobre tudo")


def _imprimir_proximos_passos(destino: Path) -> None:
    print(
        "\n[copiloto] próximos passos:\n"
        "  1. Preencha docs/copiloto/contexto/PROJECT.md (miolo + Roadmap),\n"
        "     ou rode o Bootstrapper (modo \"novo projeto\").\n"
        "  2. Gere o mapa do código:  python -m scripts.copiloto  -> Mapper.\n"
        "  3. Cole personas/<papel>.md + STATE.md no início de cada thread."
    )


def main_instalar(args: argparse.Namespace) -> int:
    destino = _resolver_destino(args.destino)
    acoes = planejar(destino)
    faltantes = planejar_gitignore(destino)

    _imprimir_plano(destino, acoes, faltantes)

    if not args.write:
        print("\n[copiloto] DRY-RUN — nada foi gravado. Use --write pra gravar.")
        return 0

    for acao in acoes:
        _aplicar_acao(acao)
    _aplicar_gitignore(destino, faltantes)

    gravados = sum(1 for a in acoes if not a.status.startswith("pular"))
    print(f"\n[copiloto] gravado: {gravados} arquivo(s) em {destino}")
    _imprimir_proximos_passos(destino)
    return 0
