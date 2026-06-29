#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════╗
║   PixieCat  v1.0.0  —  Decodificador & Analisador de Links Pix     ║
║   Autenticidade · Metadados · Relatório CyberSec PDF               ║
║                                                                      ║
║   Created by psyhusk                                                 ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import sys
import os

# Garante que módulos locais sejam encontrados
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import tkinter as tk
    from tkinter import ttk, messagebox, filedialog, scrolledtext
except ImportError:
    print("[!] tkinter ausente.")
    print("    Arch:   sudo pacman -S tk")
    print("    Debian: sudo apt install python3-tk")
    sys.exit(1)

from modules.pix_decoder   import PixDecoder
from modules.pix_analyzer  import PixAnalyzer
from modules.pix_reporter  import PixReporter
from modules.pix_ui        import PixUI
from modules.pix_config    import PixConfig

APP_NAME = "PixieCat"
VERSION  = "1.0.0"
AUTHOR   = "psyhusk"

# ── Paleta visual ─────────────────────────────────────────────────────
BG      = "#050308"
BG2     = "#080510"
BG3     = "#0d0a18"
ACCENT1 = "#7c3aed"   # violeta
ACCENT2 = "#a855f7"   # lavanda
ACCENT3 = "#c084fc"   # lila claro
BORDER  = "#4c1d95"
TEXT    = "#ede9fe"
MUTED   = "#7c6fa0"
DIM     = "#3d3560"
SUCCESS = "#22c55e"
DANGER  = "#ef4444"
WARNING = "#f59e0b"
MONO    = "#c4b5fd"


class PixieCatApp(tk.Tk):
    """Janela principal do PixieCat."""

    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME}  v{VERSION}  —  Analisador Pix Anti-Golpe")
        self.configure(bg=BG)
        self.resizable(True, True)
        self.minsize(900, 680)

        self.config_mgr  = PixConfig()
        self.decoder     = PixDecoder()
        self.analyzer    = PixAnalyzer()
        self.reporter    = PixReporter()
        self._last_result = None

        self._build_ui()
        self._center()

    # ── Layout principal ──────────────────────────────────────────────

    def _build_ui(self):
        ui = PixUI(self)

        # Título
        header = tk.Frame(self, bg=BG, pady=12)
        header.pack(fill="x", padx=18)

        tk.Label(header, text="🐱 PixieCat", font=("Courier New", 22, "bold"),
                 fg=ACCENT2, bg=BG).pack(side="left")
        tk.Label(header, text=f"  v{VERSION}  ·  Decodificador & Analisador de Links Pix",
                 font=("Courier New", 10), fg=MUTED, bg=BG).pack(side="left", pady=8)
        tk.Label(header, text=f"Created by {AUTHOR}",
                 font=("Courier New", 8), fg=DIM, bg=BG).pack(side="right")

        ui.separator(self)

        # Entrada do link
        input_frame = tk.Frame(self, bg=BG2, padx=14, pady=10)
        input_frame.pack(fill="x", padx=18, pady=(0, 4))

        tk.Label(input_frame, text="🔗  Cole o link / QR Pix aqui:",
                 font=("Courier New", 10, "bold"), fg=ACCENT3, bg=BG2).pack(anchor="w")

        entry_row = tk.Frame(input_frame, bg=BG2)
        entry_row.pack(fill="x", pady=(4, 0))

        self.entry_pix = tk.Text(entry_row, height=3,
                                 font=("Courier New", 9),
                                 bg="#0a0718", fg=TEXT,
                                 insertbackground=ACCENT2,
                                 relief="flat", bd=1,
                                 wrap="word",
                                 highlightbackground=BORDER,
                                 highlightthickness=1)
        self.entry_pix.pack(side="left", fill="x", expand=True)

        btn_frame = tk.Frame(entry_row, bg=BG2)
        btn_frame.pack(side="right", padx=(8, 0))

        ui.button(btn_frame, "⚡  ANALISAR", self._analisar,
                  color=ACCENT1).pack(fill="x", pady=(0, 4))
        ui.button(btn_frame, "🗑  Limpar", self._limpar,
                  color=DIM).pack(fill="x")

        ui.separator(self)

        # Painel de resultados — notebook com abas
        nb_frame = tk.Frame(self, bg=BG)
        nb_frame.pack(fill="both", expand=True, padx=18, pady=(0, 6))

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Pixie.TNotebook",
                         background=BG, borderwidth=0, tabmargins=[0, 0, 0, 0])
        style.configure("Pixie.TNotebook.Tab",
                         background=BG3, foreground=MUTED,
                         font=("Courier New", 9, "bold"),
                         padding=[14, 6])
        style.map("Pixie.TNotebook.Tab",
                  background=[("selected", BORDER)],
                  foreground=[("selected", TEXT)])

        self.nb = ttk.Notebook(nb_frame, style="Pixie.TNotebook")
        self.nb.pack(fill="both", expand=True)

        # Aba 1 — Decodificado
        self.tab_decode = tk.Frame(self.nb, bg=BG2)
        self.nb.add(self.tab_decode, text="📦  Decodificado")
        self._build_tab_decode()

        # Aba 2 — Análise de Autenticidade
        self.tab_auth = tk.Frame(self.nb, bg=BG2)
        self.nb.add(self.tab_auth, text="🔍  Autenticidade")
        self._build_tab_auth()

        # Aba 3 — Metadados Triangulados
        self.tab_meta = tk.Frame(self.nb, bg=BG2)
        self.nb.add(self.tab_meta, text="🧬  Metadados")
        self._build_tab_meta()

        # Aba 4 — Log
        self.tab_log = tk.Frame(self.nb, bg=BG2)
        self.nb.add(self.tab_log, text="📋  Log")
        self._build_tab_log()

        ui.separator(self)

        # Rodapé com botões de exportação
        footer = tk.Frame(self, bg=BG, pady=8)
        footer.pack(fill="x", padx=18)

        ui.button(footer, "📄  Gerar Relatório PDF", self._gerar_pdf,
                  color="#b45309").pack(side="left", padx=(0, 8))
        ui.button(footer, "📋  Copiar Resultado", self._copiar_resultado,
                  color=DIM).pack(side="left")

        self._status_var = tk.StringVar(value="Aguardando link Pix para análise…")
        tk.Label(footer, textvariable=self._status_var,
                 font=("Courier New", 8), fg=MUTED, bg=BG).pack(side="right")

    # ── Abas ──────────────────────────────────────────────────────────

    def _build_tab_decode(self):
        f = self.tab_decode
        tk.Label(f, text="Campos decodificados do payload EMV/Pix:",
                 font=("Courier New", 9), fg=MUTED, bg=BG2).pack(anchor="w", padx=10, pady=(8, 2))

        cols = ("Campo", "ID", "Valor")
        self.tree_decode = ttk.Treeview(f, columns=cols, show="headings", height=14)
        for c, w in zip(cols, [220, 60, 420]):
            self.tree_decode.heading(c, text=c)
            self.tree_decode.column(c, width=w, anchor="w")

        style = ttk.Style()
        style.configure("Treeview",
                         background="#0a0718", fieldbackground="#0a0718",
                         foreground=TEXT, rowheight=22,
                         font=("Courier New", 8))
        style.configure("Treeview.Heading",
                         background=BG3, foreground=ACCENT3,
                         font=("Courier New", 8, "bold"))
        style.map("Treeview", background=[("selected", BORDER)])

        sb = ttk.Scrollbar(f, orient="vertical", command=self.tree_decode.yview)
        self.tree_decode.configure(yscrollcommand=sb.set)
        self.tree_decode.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=4)
        sb.pack(side="right", fill="y", pady=4, padx=(0, 4))

    def _build_tab_auth(self):
        f = self.tab_auth

        self.auth_canvas = tk.Canvas(f, bg=BG2, highlightthickness=0)
        sb = ttk.Scrollbar(f, orient="vertical", command=self.auth_canvas.yview)
        self.auth_canvas.configure(yscrollcommand=sb.set)
        self.auth_inner = tk.Frame(self.auth_canvas, bg=BG2)
        self.auth_win = self.auth_canvas.create_window((0, 0), window=self.auth_inner, anchor="nw")
        self.auth_inner.bind("<Configure>",
            lambda e: self.auth_canvas.configure(scrollregion=self.auth_canvas.bbox("all")))
        self.auth_canvas.bind("<Configure>",
            lambda e: self.auth_canvas.itemconfig(self.auth_win, width=e.width))
        self.auth_canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        tk.Label(self.auth_inner, text="Execute uma análise para ver resultados de autenticidade.",
                 font=("Courier New", 9), fg=MUTED, bg=BG2).pack(pady=20)

    def _build_tab_meta(self):
        f = self.tab_meta

        self.meta_text = scrolledtext.ScrolledText(f,
            font=("Courier New", 9), bg="#050310", fg=MONO,
            relief="flat", bd=0, state="disabled", wrap="word")
        self.meta_text.pack(fill="both", expand=True, padx=8, pady=8)

    def _build_tab_log(self):
        f = self.tab_log

        self.log_text = scrolledtext.ScrolledText(f,
            font=("Courier New", 8), bg="#050310", fg="#6b7280",
            relief="flat", bd=0, state="disabled", wrap="word")
        self.log_text.pack(fill="both", expand=True, padx=8, pady=8)

        tk.Button(f, text="🗑  Limpar Log",
                  font=("Courier New", 8), bg=BG3, fg=MUTED,
                  relief="flat", bd=0, cursor="hand2",
                  command=self._limpar_log).pack(anchor="e", padx=8, pady=(0, 4))

    # ── Ações ─────────────────────────────────────────────────────────

    def _analisar(self):
        raw = self.entry_pix.get("1.0", "end").strip()
        if not raw:
            messagebox.showwarning("PixieCat", "Cole um link ou payload Pix antes de analisar.")
            return

        self._log(f"[>>] Iniciando análise: {raw[:80]}{'…' if len(raw) > 80 else ''}")
        self._status("🔍  Decodificando payload…")

        try:
            decoded = self.decoder.decode(raw)
        except Exception as e:
            self._log(f"[!!] Erro na decodificação: {e}")
            self._status("❌  Falha na decodificação", error=True)
            messagebox.showerror("Erro", f"Não foi possível decodificar:\n{e}")
            return

        self._log(f"[OK] Decodificados {len(decoded['fields'])} campos EMV.")

        try:
            analysis = self.analyzer.analyze(decoded)
        except Exception as e:
            self._log(f"[!!] Erro na análise: {e}")
            analysis = {"score": 0, "flags": [], "details": {}}

        self._last_result = {"raw": raw, "decoded": decoded, "analysis": analysis}

        self._preencher_decode(decoded)
        self._preencher_auth(analysis)
        self._preencher_meta(decoded, analysis)

        score = analysis.get("score", 100)
        if score >= 80:
            self._status(f"✅  Análise concluída — Risco BAIXO  ({score}/100)")
        elif score >= 50:
            self._status(f"⚠️   Análise concluída — Risco MÉDIO  ({score}/100)", warn=True)
        else:
            self._status(f"🚨  Análise concluída — Risco ALTO  ({score}/100)", error=True)

        self._log(f"[>>] Pontuação de autenticidade: {score}/100")
        self.nb.select(0)

    def _preencher_decode(self, decoded):
        for row in self.tree_decode.get_children():
            self.tree_decode.delete(row)
        for field in decoded.get("fields", []):
            self.tree_decode.insert("", "end",
                values=(field["name"], field["id"], field["value"]))

    def _preencher_auth(self, analysis):
        for w in self.auth_inner.winfo_children():
            w.destroy()

        score = analysis.get("score", 0)
        flags = analysis.get("flags", [])
        checks = analysis.get("checks", [])

        # Score visual
        color = SUCCESS if score >= 80 else (WARNING if score >= 50 else DANGER)
        score_f = tk.Frame(self.auth_inner, bg=BG3, padx=14, pady=10)
        score_f.pack(fill="x", padx=10, pady=(10, 4))
        tk.Label(score_f, text="Pontuação de Autenticidade",
                 font=("Courier New", 9), fg=MUTED, bg=BG3).pack(anchor="w")
        tk.Label(score_f, text=f"{score} / 100",
                 font=("Courier New", 26, "bold"), fg=color, bg=BG3).pack(anchor="w")

        nivel = "BAIXO ✅" if score >= 80 else ("MÉDIO ⚠️" if score >= 50 else "ALTO 🚨")
        tk.Label(score_f, text=f"Nível de Risco: {nivel}",
                 font=("Courier New", 11, "bold"), fg=color, bg=BG3).pack(anchor="w")

        # Checklist
        tk.Label(self.auth_inner, text="Verificações realizadas:",
                 font=("Courier New", 9, "bold"), fg=ACCENT3, bg=BG2).pack(anchor="w", padx=12, pady=(8, 2))

        for chk in checks:
            row = tk.Frame(self.auth_inner, bg=BG2)
            row.pack(fill="x", padx=12, pady=1)
            ic = "✅" if chk["ok"] else "❌"
            c  = SUCCESS if chk["ok"] else DANGER
            tk.Label(row, text=f"{ic}  {chk['label']}",
                     font=("Courier New", 9), fg=c, bg=BG2, anchor="w").pack(side="left")
            tk.Label(row, text=chk.get("detail", ""),
                     font=("Courier New", 8), fg=MUTED, bg=BG2, anchor="e").pack(side="right")

        # Flags de alerta
        if flags:
            tk.Label(self.auth_inner, text="⚠  Alertas detectados:",
                     font=("Courier New", 9, "bold"), fg=WARNING, bg=BG2).pack(anchor="w", padx=12, pady=(10, 2))
            for fl in flags:
                tk.Label(self.auth_inner, text=f"  ⚑  {fl}",
                         font=("Courier New", 8), fg=WARNING, bg=BG2, anchor="w").pack(anchor="w", padx=14)

    def _preencher_meta(self, decoded, analysis):
        self.meta_text.configure(state="normal")
        self.meta_text.delete("1.0", "end")
        lines = []
        lines.append("═" * 60)
        lines.append("  METADADOS TRIANGULADOS — PixieCat")
        lines.append("═" * 60)

        meta = decoded.get("metadata", {})
        sections = [
            ("RECEPTOR (Beneficiário)", [
                ("Nome",         meta.get("nome", "—")),
                ("Chave Pix",    meta.get("chave", "—")),
                ("Tipo de Chave",meta.get("tipo_chave", "—")),
                ("ISPB do PSP",  meta.get("ispb", "—")),
                ("Banco",        meta.get("banco", "—")),
                ("Cidade",       meta.get("cidade", "—")),
                ("CEP",          meta.get("cep", "—")),
            ]),
            ("TRANSAÇÃO", [
                ("Valor",        meta.get("valor", "Não especificado")),
                ("Moeda",        meta.get("moeda", "BRL")),
                ("TxID",         meta.get("txid", "—")),
                ("Descrição",    meta.get("descricao", "—")),
                ("URL Payload",  meta.get("url", "—")),
            ]),
            ("INTEGRIDADE", [
                ("CRC-16 calculado", decoded.get("crc_calculated", "—")),
                ("CRC-16 no payload", decoded.get("crc_payload", "—")),
                ("CRC válido",   "✅ SIM" if decoded.get("crc_valid") else "❌ NÃO"),
                ("Formato",      decoded.get("format", "—")),
                ("Versão EMV",   decoded.get("version", "—")),
            ]),
            ("ANÁLISE DE RISCO", [
                ("Score",        f"{analysis.get('score', '—')}/100"),
                ("Nível",        analysis.get("nivel", "—")),
                ("Alertas",      str(len(analysis.get("flags", [])))),
            ]),
        ]

        for title, rows in sections:
            lines.append("")
            lines.append(f"┌─ {title} " + "─" * (54 - len(title)))
            for k, v in rows:
                lines.append(f"│  {k:<22} {v}")
            lines.append("└" + "─" * 59)

        if analysis.get("flags"):
            lines.append("")
            lines.append("⚠  ALERTAS DE AUTENTICIDADE:")
            for fl in analysis["flags"]:
                lines.append(f"   ⚑  {fl}")

        lines.append("")
        lines.append("═" * 60)

        self.meta_text.insert("end", "\n".join(lines))
        self.meta_text.configure(state="disabled")

    def _gerar_pdf(self):
        if not self._last_result:
            messagebox.showwarning("PixieCat", "Realize uma análise antes de gerar o relatório.")
            return

        path = filedialog.asksaveasfilename(
            title="Salvar Relatório PDF",
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            initialfile="relatorio_pix_pixiecat.pdf"
        )
        if not path:
            return

        self._log(f"[>>] Gerando relatório PDF: {path}")
        self._status("📄  Gerando PDF…")

        try:
            self.reporter.generate(self._last_result, path)
            self._log(f"[OK] Relatório salvo: {path}")
            self._status(f"✅  PDF salvo: {path}")
            messagebox.showinfo("PixieCat", f"Relatório salvo com sucesso!\n{path}")
        except Exception as e:
            self._log(f"[!!] Erro ao gerar PDF: {e}")
            self._status("❌  Falha ao gerar PDF", error=True)
            messagebox.showerror("Erro", f"Falha ao gerar PDF:\n{e}")

    def _copiar_resultado(self):
        if not self._last_result:
            return
        self.clipboard_clear()
        txt = self.meta_text.get("1.0", "end")
        self.clipboard_append(txt)
        self._status("📋  Resultado copiado para a área de transferência")

    def _limpar(self):
        self.entry_pix.delete("1.0", "end")
        for row in self.tree_decode.get_children():
            self.tree_decode.delete(row)
        for w in self.auth_inner.winfo_children():
            w.destroy()
        self.meta_text.configure(state="normal")
        self.meta_text.delete("1.0", "end")
        self.meta_text.configure(state="disabled")
        self._last_result = None
        self._status("Aguardando link Pix para análise…")

    def _limpar_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    def _log(self, msg):
        import datetime
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"[{ts}] {msg}\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _status(self, msg, error=False, warn=False):
        self._status_var.set(msg)

    def _center(self):
        self.update_idletasks()
        w, h = 960, 720
        x = (self.winfo_screenwidth()  - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")


if __name__ == "__main__":
    app = PixieCatApp()
    app.mainloop()
