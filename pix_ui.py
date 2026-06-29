#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
modules/pix_ui.py
Componentes de UI reutilizáveis para o PixieCat.
Created by psyhusk
"""

import tkinter as tk

BG      = "#050308"
BG2     = "#080510"
BG3     = "#0d0a18"
ACCENT1 = "#7c3aed"
ACCENT2 = "#a855f7"
ACCENT3 = "#c084fc"
BORDER  = "#4c1d95"
TEXT    = "#ede9fe"
MUTED   = "#7c6fa0"
DIM     = "#3d3560"


class PixUI:
    """Utilitários de interface gráfica do PixieCat."""

    def __init__(self, root):
        self.root = root

    def separator(self, parent):
        tk.Frame(parent, bg=BORDER, height=1).pack(fill="x", padx=18, pady=2)

    def button(self, parent, text: str, command, color: str = ACCENT1) -> tk.Button:
        return tk.Button(
            parent,
            text=text,
            font=("Courier New", 9, "bold"),
            bg=color,
            fg=TEXT,
            activebackground=BORDER,
            activeforeground=TEXT,
            relief="flat",
            bd=0,
            padx=12,
            pady=6,
            cursor="hand2",
            command=command,
        )

    def label(self, parent, text: str, size: int = 9,
              color: str = TEXT, bold: bool = False) -> tk.Label:
        weight = "bold" if bold else "normal"
        return tk.Label(
            parent,
            text=text,
            font=("Courier New", size, weight),
            fg=color,
            bg=parent.cget("bg"),
        )

    def card(self, parent, title: str = "", padx: int = 14, pady: int = 10) -> tk.Frame:
        frame = tk.Frame(parent, bg=BG3, padx=padx, pady=pady)
        if title:
            tk.Label(frame, text=title,
                     font=("Courier New", 9, "bold"),
                     fg=ACCENT3, bg=BG3).pack(anchor="w", pady=(0, 4))
        return frame
