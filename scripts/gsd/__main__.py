"""
Entry point do CLI: python -m scripts.gsd

Gera o snapshot estático (árvore + assinaturas) em .temp/codebase-snapshot.txt.
A seção de schemas sai com nota explicativa porque o pipeline não rodou.

Pra incluir schemas, use a API runtime no main.py do pipeline:

    from scripts.gsd import registry, snapshot_completo
    registry.add("balancete", df_balancete)
    # ...
    snapshot_completo()
"""
from __future__ import annotations

import sys

from scripts.gsd.snapshot import snapshot_completo


def main() -> int:
    try:
        snapshot_completo()
    except Exception as exc:
        print(f"[gsd] ERRO: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
