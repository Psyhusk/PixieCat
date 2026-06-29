#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
modules/pix_config.py
Gerenciador de configurações do PixieCat.
Created by psyhusk
"""

import json
from pathlib import Path

CONFIG_DIR  = Path.home() / ".pixiecat"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULTS = {
    "tema":            "violeta",
    "salvar_historico": True,
    "dir_relatorios":   str(Path.home() / "Documentos"),
    "version":          "1.0.0",
    "author":           "psyhusk",
}


class PixConfig:
    """Carrega e salva configurações do PixieCat em ~/.pixiecat/config.json."""

    def __init__(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        self._cfg = self._load()

    def _load(self) -> dict:
        if CONFIG_FILE.exists():
            try:
                data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
                return {**DEFAULTS, **data}
            except Exception:
                pass
        self._save(DEFAULTS)
        return dict(DEFAULTS)

    def _save(self, cfg: dict):
        CONFIG_FILE.write_text(json.dumps(cfg, indent=2, ensure_ascii=False),
                               encoding="utf-8")

    def get(self, key: str, default=None):
        return self._cfg.get(key, default)

    def set(self, key: str, value):
        self._cfg[key] = value
        self._save(self._cfg)
