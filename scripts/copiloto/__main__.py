"""
Entry point do CLI: python -m scripts.copiloto

Dois subcomandos:

    python -m scripts.copiloto
        Gera o snapshot estático (árvore + assinaturas) em
        .temp/codebase-snapshot.txt. A seção de schemas sai com nota
        explicativa porque o pipeline não rodou. Pra incluir schemas, use a
        API runtime no main.py do pipeline:

            from scripts.copiloto import registry, snapshot_completo
            registry.add("balancete", df_balancete)
            # ...
            snapshot_completo()

    python -m scripts.copiloto pack <path> [<path> ...]
        Empacota arquivos/pastas no formato `=== ARQUIVO: path ===` em
        .temp/pack.txt e ecoa na stdout, pra colar no chat quando uma persona
        pede contexto. Pasta é varrida recursivamente pelos arquivos de texto.

    python -m scripts.copiloto aplicar [--write]
        Lê a resposta raw da persona (de llm_output.md ou do clipboard) e grava
        os artefatos .md que ela delimitou com <!-- INICIO: ... --> / <!-- FIM:
        ... -->, além de fazer merge dos blocos UPDATE STATE.md / UPDATE
        PROJECT.md. Dry-run por padrão; --write grava.
"""
from __future__ import annotations

import argparse
import sys

from scripts.copiloto.snapshot import snapshot_completo


def _construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m scripts.copiloto",
        description="Utilitários de contexto do Copilot em Casa.",
    )
    sub = parser.add_subparsers(dest="comando")

    p_pack = sub.add_parser(
        "pack",
        help="empacota arquivos/pastas pra colar no chat (=== ARQUIVO: path ===)",
    )
    p_pack.add_argument(
        "paths",
        nargs="+",
        metavar="PATH",
        help="arquivos ou pastas (pasta é varrida recursivamente)",
    )

    p_aplicar = sub.add_parser(
        "aplicar",
        help="materializa os artefatos .md da resposta da persona (llm_output.md ou clipboard)",
    )
    p_aplicar.add_argument(
        "--write",
        action="store_true",
        help="grava de fato (sem isso, é dry-run: só mostra o que faria)",
    )
    p_aplicar.add_argument(
        "--sem-h1",
        action="store_true",
        help="não inserir H1 sintético quando o .md não tiver título",
    )
    p_aplicar.add_argument(
        "--diff",
        action="store_true",
        help="mostrar o diff também ao gravar (--write)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _construir_parser().parse_args(argv)

    try:
        if args.comando == "pack":
            from scripts.copiloto.pack import ARQUIVO_PACK, empacotar

            # Console do Windows é cp1252 por padrão: sem isso, acento vai
            # quebrado pra stdout (e pro que você cola no chat).
            if hasattr(sys.stdout, "reconfigure"):
                sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]

            texto = empacotar(args.paths)
            print(texto)
            print(f"[copiloto] (também salvo em {ARQUIVO_PACK})", file=sys.stderr)
        elif args.comando == "aplicar":
            from scripts.copiloto.aplicar import main_aplicar

            if hasattr(sys.stdout, "reconfigure"):
                sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
            return main_aplicar(args)
        else:
            snapshot_completo()
    except Exception as exc:
        print(f"[copiloto] ERRO: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
