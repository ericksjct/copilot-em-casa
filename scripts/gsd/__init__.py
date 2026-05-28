"""
scripts.gsd — utilitários do fluxo GSD emulado no Copilot.

Duas portas de uso:

1. CLI estática (sem pipeline rodando):
       python -m scripts.gsd

2. API runtime (no main.py do pipeline):
       from scripts.gsd import registry, snapshot_completo

       df_balancete = carregar_balancete()
       registry.add("balancete", df_balancete)
       # ... resto do pipeline ...
       snapshot_completo()

Saída: .temp/codebase-snapshot.txt na raiz do repo.
"""
from __future__ import annotations

from scripts.gsd.schemas import registry
from scripts.gsd.snapshot import snapshot_architect, snapshot_completo

__all__ = ["registry", "snapshot_completo", "snapshot_architect"]
