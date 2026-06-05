"""
scripts.copiloto — utilitários do Copilot em Casa.

Duas portas de uso:

1. CLI estática (sem pipeline rodando):
       python -m scripts.copiloto

2. API runtime (no main.py do pipeline):
       from scripts.copiloto import registry, snapshot_completo

       df_balancete = carregar_balancete()
       registry.add("balancete", df_balancete)
       # ... resto do pipeline ...
       snapshot_completo()

Saída: .temp/codebase-snapshot.txt na raiz do repo.
"""
from __future__ import annotations

from scripts.copiloto.schemas import registry
from scripts.copiloto.snapshot import snapshot_amostras, snapshot_completo

__all__ = ["registry", "snapshot_completo", "snapshot_amostras"]
