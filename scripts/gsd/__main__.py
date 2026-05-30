"""
Entry point do CLI: python -m scripts.gsd

Dois subcomandos:

    python -m scripts.gsd
        Gera o snapshot estático (árvore + assinaturas) em
        .temp/codebase-snapshot.txt. A seção de schemas sai com nota
        explicativa porque o pipeline não rodou. Pra incluir schemas, use a
        API runtime no main.py do pipeline:

            from scripts.gsd import registry, snapshot_completo
            registry.add("balancete", df_balancete)
            # ...
            snapshot_completo()

    python -m scripts.gsd pack <path> [<path> ...]
        Empacota arquivos/pastas no formato `=== ARQUIVO: path ===` em
        .temp/pack.txt e ecoa na stdout, pra colar no chat quando uma persona
        pede contexto. Pasta é varrida recursivamente pelos arquivos de texto.
"""
from __future__ import annotations

import argparse
import sys

from scripts.gsd.snapshot import snapshot_completo


def _construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m scripts.gsd",
        description="Utilitários de contexto do fluxo GSD emulado no Copilot.",
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
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _construir_parser().parse_args(argv)

    try:
        if args.comando == "pack":
            from scripts.gsd.pack import ARQUIVO_PACK, empacotar

            # Console do Windows é cp1252 por padrão: sem isso, acento vai
            # quebrado pra stdout (e pro que você cola no chat).
            if hasattr(sys.stdout, "reconfigure"):
                sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]

            texto = empacotar(args.paths)
            print(texto)
            print(f"[gsd] (também salvo em {ARQUIVO_PACK})", file=sys.stderr)
        else:
            snapshot_completo()
    except Exception as exc:
        print(f"[gsd] ERRO: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
