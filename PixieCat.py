#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════╗
║   PixieCat  v1.1.0  —  Decodificador & Analisador de Links Pix     ║
║   Autenticidade · Metadados · Telemetria · Relatório CyberSec PDF  ║
║                                                                      ║
║   Created by psyhusk                                                 ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import sys, os, threading
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import tkinter as tk
    from tkinter import ttk, messagebox, filedialog, scrolledtext
except ImportError:
    print("[!] tkinter ausente.\n    Arch: sudo pacman -S tk\n    Debian: sudo apt install python3-tk")
    sys.exit(1)

from modules.pix_decoder   import PixDecoder
from modules.pix_analyzer  import PixAnalyzer
from modules.pix_reporter  import PixReporter
from modules.pix_telemetry import PixTelemetry, TelemetryReport
from modules.pix_ui        import PixUI
from modules.pix_config    import PixConfig

APP_NAME = "PixieCat"
VERSION  = "1.1.0"
AUTHOR   = "psyhusk"

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
SUCCESS = "#22c55e"
DANGER  = "#ef4444"
WARNING = "#f59e0b"
MONO    = "#c4b5fd"


class PixieCatApp(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME}  v{VERSION}  —  Analisador Pix Anti-Golpe")
        self.configure(bg=BG)
        self.resizable(True, True)
        self.minsize(900, 700)

        self.config_mgr   = PixConfig()
        self.decoder      = PixDecoder()
        self.analyzer     = PixAnalyzer()
        self.reporter     = PixReporter()
        self.telemetry    = PixTelemetry(callback=self._log)
        self._last_result = None
        self._tel_report  = None

        self._build_ui()
        self._center()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── Layout principal ──────────────────────────────────────────────

    def _build_ui(self):
        ui = PixUI(self)

        # Título
        header = tk.Frame(self, bg=BG, pady=10)
        header.pack(fill="x", padx=18)
        tk.Label(header, text="🐱 PixieCat", font=("Courier New", 22, "bold"),
                 fg=ACCENT2, bg=BG).pack(side="left")
        tk.Label(header, text=f"  v{VERSION}  ·  Decodificador & Analisador de Links Pix",
                 font=("Courier New", 10), fg=MUTED, bg=BG).pack(side="left", pady=8)
        tk.Label(header, text=f"Created by {AUTHOR}",
                 font=("Courier New", 8), fg=DIM, bg=BG).pack(side="right")

        ui.separator(self)

        # Entrada
        input_frame = tk.Frame(self, bg=BG2, padx=14, pady=10)
        input_frame.pack(fill="x", padx=18, pady=(0, 4))
        tk.Label(input_frame, text="🔗  Cole o link / QR Pix aqui:",
                 font=("Courier New", 10, "bold"), fg=ACCENT3, bg=BG2).pack(anchor="w")
        entry_row = tk.Frame(input_frame, bg=BG2)
        entry_row.pack(fill="x", pady=(4, 0))
        self.entry_pix = tk.Text(entry_row, height=3,
                                 font=("Courier New", 9), bg="#0a0718", fg=TEXT,
                                 insertbackground=ACCENT2, relief="flat", bd=1,
                                 wrap="word", highlightbackground=BORDER,
                                 highlightthickness=1)
        self.entry_pix.pack(side="left", fill="x", expand=True)
        btn_frame = tk.Frame(entry_row, bg=BG2)
        btn_frame.pack(side="right", padx=(8, 0))
        ui.button(btn_frame, "⚡  ANALISAR",  self._analisar,  color=ACCENT1).pack(fill="x", pady=(0, 4))
        ui.button(btn_frame, "🌐  + Telemetria", self._analisar_com_telemetria, color="#0f766e").pack(fill="x", pady=(0, 4))
        ui.button(btn_frame, "🗑  Limpar",    self._limpar,    color=DIM).pack(fill="x")

        ui.separator(self)

        # Notebook
        nb_frame = tk.Frame(self, bg=BG)
        nb_frame.pack(fill="both", expand=True, padx=18, pady=(0, 6))

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Pixie.TNotebook", background=BG, borderwidth=0, tabmargins=[0,0,0,0])
        style.configure("Pixie.TNotebook.Tab", background=BG3, foreground=MUTED,
                         font=("Courier New", 9, "bold"), padding=[12, 6])
        style.map("Pixie.TNotebook.Tab",
                  background=[("selected", BORDER)], foreground=[("selected", TEXT)])

        self.nb = ttk.Notebook(nb_frame, style="Pixie.TNotebook")
        self.nb.pack(fill="both", expand=True)

        self.tab_decode = tk.Frame(self.nb, bg=BG2)
        self.nb.add(self.tab_decode, text="📦  Decodificado")
        self._build_tab_decode()

        self.tab_auth = tk.Frame(self.nb, bg=BG2)
        self.nb.add(self.tab_auth, text="🔍  Autenticidade")
        self._build_tab_auth()

        self.tab_meta = tk.Frame(self.nb, bg=BG2)
        self.nb.add(self.tab_meta, text="🧬  Metadados")
        self._build_tab_meta()

        self.tab_tel = tk.Frame(self.nb, bg=BG2)
        self.nb.add(self.tab_tel, text="📡  Telemetria")
        self._build_tab_tel()

        self.tab_log = tk.Frame(self.nb, bg=BG2)
        self.nb.add(self.tab_log, text="📋  Log")
        self._build_tab_log()

        ui.separator(self)

        # Rodapé
        footer = tk.Frame(self, bg=BG, pady=8)
        footer.pack(fill="x", padx=18)
        ui.button(footer, "📄  Gerar Relatório PDF", self._gerar_pdf,  color="#b45309").pack(side="left", padx=(0,8))
        ui.button(footer, "📋  Copiar Resultado",    self._copiar,     color=DIM).pack(side="left")
        self._status_var = tk.StringVar(value="Aguardando link Pix…")
        tk.Label(footer, textvariable=self._status_var,
                 font=("Courier New", 8), fg=MUTED, bg=BG).pack(side="right")

    # ── Abas ──────────────────────────────────────────────────────────

    def _build_tab_decode(self):
        f = self.tab_decode
        tk.Label(f, text="Campos decodificados do payload EMV/Pix:",
                 font=("Courier New", 9), fg=MUTED, bg=BG2).pack(anchor="w", padx=10, pady=(8,2))
        cols = ("Campo", "ID", "Valor")
        self.tree_decode = ttk.Treeview(f, columns=cols, show="headings", height=14)
        for c, w in zip(cols, [220, 60, 420]):
            self.tree_decode.heading(c, text=c)
            self.tree_decode.column(c, width=w, anchor="w")
        style = ttk.Style()
        style.configure("Treeview", background="#0a0718", fieldbackground="#0a0718",
                         foreground=TEXT, rowheight=22, font=("Courier New", 8))
        style.configure("Treeview.Heading", background=BG3, foreground=ACCENT3,
                         font=("Courier New", 8, "bold"))
        style.map("Treeview", background=[("selected", BORDER)])
        sb = ttk.Scrollbar(f, orient="vertical", command=self.tree_decode.yview)
        self.tree_decode.configure(yscrollcommand=sb.set)
        self.tree_decode.pack(side="left", fill="both", expand=True, padx=(10,0), pady=4)
        sb.pack(side="right", fill="y", pady=4, padx=(0,4))

    def _build_tab_auth(self):
        f = self.tab_auth
        self.auth_canvas = tk.Canvas(f, bg=BG2, highlightthickness=0)
        sb = ttk.Scrollbar(f, orient="vertical", command=self.auth_canvas.yview)
        self.auth_canvas.configure(yscrollcommand=sb.set)
        self.auth_inner = tk.Frame(self.auth_canvas, bg=BG2)
        self.auth_win   = self.auth_canvas.create_window((0,0), window=self.auth_inner, anchor="nw")
        self.auth_inner.bind("<Configure>",
            lambda e: self.auth_canvas.configure(scrollregion=self.auth_canvas.bbox("all")))
        self.auth_canvas.bind("<Configure>",
            lambda e: self.auth_canvas.itemconfig(self.auth_win, width=e.width))
        self.auth_canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        tk.Label(self.auth_inner, text="Execute uma análise para ver autenticidade.",
                 font=("Courier New", 9), fg=MUTED, bg=BG2).pack(pady=20)

    def _build_tab_meta(self):
        f = self.tab_meta
        self.meta_text = scrolledtext.ScrolledText(
            f, font=("Courier New", 9), bg="#050310", fg=MONO,
            relief="flat", bd=0, state="disabled", wrap="word")
        self.meta_text.pack(fill="both", expand=True, padx=8, pady=8)

    def _build_tab_tel(self):
        f = self.tab_tel

        # Painel de status da telemetria
        top = tk.Frame(f, bg=BG3, padx=12, pady=8)
        top.pack(fill="x", padx=8, pady=(8,4))
        tk.Label(top, text="📡  Motor de Telemetria — Enriquecimento de Metadados Pix",
                 font=("Courier New", 9, "bold"), fg=ACCENT3, bg=BG3).pack(anchor="w")
        tk.Label(top,
                 text="Triangulação de CEP por 3 fontes · DNS/rDNS · TLS fingerprint · GeoIP · PSP lookup",
                 font=("Courier New", 8), fg=MUTED, bg=BG3).pack(anchor="w")

        self._tel_status_var = tk.StringVar(value="Aguardando análise com telemetria…")
        self._tel_status_lbl = tk.Label(top, textvariable=self._tel_status_var,
                                         font=("Courier New", 9, "bold"), fg=MUTED, bg=BG3)
        self._tel_status_lbl.pack(anchor="w", pady=(4,0))

        # Notebook interno da aba telemetria
        tel_nb_frame = tk.Frame(f, bg=BG2)
        tel_nb_frame.pack(fill="both", expand=True, padx=8, pady=4)

        style = ttk.Style()
        style.configure("Tel.TNotebook", background=BG2, borderwidth=0, tabmargins=[0,0,0,0])
        style.configure("Tel.TNotebook.Tab", background=BG3, foreground=MUTED,
                         font=("Courier New", 8, "bold"), padding=[10,4])
        style.map("Tel.TNotebook.Tab",
                  background=[("selected", DIM)], foreground=[("selected", ACCENT3)])

        self.tel_nb = ttk.Notebook(tel_nb_frame, style="Tel.TNotebook")
        self.tel_nb.pack(fill="both", expand=True)

        # Sub-abas
        self.tel_cep_frame = tk.Frame(self.tel_nb, bg=BG2)
        self.tel_nb.add(self.tel_cep_frame, text="📮  CEP Triangulado")
        self._build_tel_cep()

        self.tel_net_frame = tk.Frame(self.tel_nb, bg=BG2)
        self.tel_nb.add(self.tel_net_frame, text="🌐  Rede / DNS / TLS")
        self._build_tel_net()

        self.tel_geo_frame = tk.Frame(self.tel_nb, bg=BG2)
        self.tel_nb.add(self.tel_geo_frame, text="🗺  GeoIP")
        self._build_tel_geo()

        self.tel_anom_frame = tk.Frame(self.tel_nb, bg=BG2)
        self.tel_nb.add(self.tel_anom_frame, text="⚠  Anomalias")
        self._build_tel_anom()

    def _build_tel_cep(self):
        f = self.tel_cep_frame
        self.tel_cep_text = scrolledtext.ScrolledText(
            f, font=("Courier New", 9), bg="#050310", fg=MONO,
            relief="flat", bd=0, state="disabled", wrap="word")
        self.tel_cep_text.pack(fill="both", expand=True, padx=8, pady=8)

    def _build_tel_net(self):
        f = self.tel_net_frame
        self.tel_net_text = scrolledtext.ScrolledText(
            f, font=("Courier New", 9), bg="#050310", fg=MONO,
            relief="flat", bd=0, state="disabled", wrap="word")
        self.tel_net_text.pack(fill="both", expand=True, padx=8, pady=8)

    def _build_tel_geo(self):
        f = self.tel_geo_frame
        self.tel_geo_text = scrolledtext.ScrolledText(
            f, font=("Courier New", 9), bg="#050310", fg=MONO,
            relief="flat", bd=0, state="disabled", wrap="word")
        self.tel_geo_text.pack(fill="both", expand=True, padx=8, pady=8)

    def _build_tel_anom(self):
        f = self.tel_anom_frame
        self.tel_anom_text = scrolledtext.ScrolledText(
            f, font=("Courier New", 9), bg="#050310", fg=WARNING,
            relief="flat", bd=0, state="disabled", wrap="word")
        self.tel_anom_text.pack(fill="both", expand=True, padx=8, pady=8)

    def _build_tab_log(self):
        f = self.tab_log
        self.log_text = scrolledtext.ScrolledText(
            f, font=("Courier New", 8), bg="#050310", fg="#6b7280",
            relief="flat", bd=0, state="disabled", wrap="word")
        self.log_text.pack(fill="both", expand=True, padx=8, pady=8)
        tk.Button(f, text="🗑  Limpar Log", font=("Courier New", 8),
                  bg=BG3, fg=MUTED, relief="flat", bd=0, cursor="hand2",
                  command=self._limpar_log).pack(anchor="e", padx=8, pady=(0,4))

    # ── Ações ─────────────────────────────────────────────────────────

    def _analisar(self, com_telemetria: bool = False):
        raw = self.entry_pix.get("1.0", "end").strip()
        if not raw:
            messagebox.showwarning("PixieCat", "Cole um link ou payload Pix antes de analisar.")
            return
        self._log(f"[>>] Análise iniciada: {raw[:80]}{'…' if len(raw)>80 else ''}")
        self._status("🔍  Decodificando…")
        try:
            decoded  = self.decoder.decode(raw)
        except Exception as e:
            self._log(f"[!!] Erro: {e}")
            self._status("❌  Falha na decodificação", error=True)
            messagebox.showerror("Erro", f"Não foi possível decodificar:\n{e}")
            return
        self._log(f"[OK] {len(decoded['fields'])} campos EMV decodificados")
        try:
            analysis = self.analyzer.analyze(decoded)
        except Exception as e:
            self._log(f"[!!] Análise: {e}")
            analysis = {"score":0,"flags":[],"checks":[],"nivel":"?"}

        self._last_result = {"raw":raw, "decoded":decoded, "analysis":analysis}
        self._preencher_decode(decoded)
        self._preencher_auth(analysis)
        self._preencher_meta(decoded, analysis, tel=None)

        score = analysis.get("score", 100)
        self._status_score(score)
        self._log(f"[>>] Score: {score}/100 — {analysis.get('nivel')}")
        self.nb.select(0)

        if com_telemetria:
            self._iniciar_telemetria(decoded, analysis)

    def _analisar_com_telemetria(self):
        self._analisar(com_telemetria=True)

    def _iniciar_telemetria(self, decoded: dict, analysis: dict):
        meta = decoded.get("metadata", {})
        self._status("📡  Telemetria em andamento…")
        self._tel_status("⏳  Coletando dados… (paralelo)")
        self._log("[TEL] Motor de telemetria iniciado")
        self.nb.select(3)   # aba Telemetria

        def run():
            tel = self.telemetry.enrich(meta, decoded)
            self.after(0, lambda: self._on_telemetria(tel, analysis))

        threading.Thread(target=run, daemon=True).start()

    def _on_telemetria(self, tel: TelemetryReport, analysis: dict):
        self._tel_report = tel

        # Aplica delta de score da telemetria
        score_adj = max(0, min(100, analysis.get("score", 100) + tel.score_delta))
        if tel.score_delta != 0:
            analysis["score"] = score_adj
            self._log(f"[TEL] Score ajustado por telemetria: delta={tel.score_delta} → {score_adj}/100")
            if self._last_result:
                self._last_result["analysis"] = analysis
                self._preencher_auth(analysis)
                self._preencher_meta(
                    self._last_result["decoded"], analysis, tel=tel)

        self._preencher_tel(tel)
        self._status_score(score_adj)
        self._tel_status(
            f"✅  Concluído em {tel.duracao_total_ms:.0f}ms — "
            f"{len(tel.cep_fontes)} fontes CEP, "
            f"{len(tel.anomalias)} anomalia(s)"
        )
        self._log(f"[TEL] Relatório pronto — sessão {tel.session_id}")

    # ── Preenchimento das abas ─────────────────────────────────────────

    def _preencher_decode(self, decoded):
        for row in self.tree_decode.get_children():
            self.tree_decode.delete(row)
        for f in decoded.get("fields", []):
            self.tree_decode.insert("", "end", values=(f["name"], f["id"], f["value"]))
            for sub in f.get("sub", []):
                self.tree_decode.insert("", "end",
                    values=(f"  └─ {sub['name']}", sub["id"], sub["value"]))

    def _preencher_auth(self, analysis):
        for w in self.auth_inner.winfo_children():
            w.destroy()
        score  = analysis.get("score", 0)
        flags  = analysis.get("flags", [])
        checks = analysis.get("checks", [])
        color  = SUCCESS if score >= 80 else (WARNING if score >= 50 else DANGER)

        sf = tk.Frame(self.auth_inner, bg=BG3, padx=14, pady=10)
        sf.pack(fill="x", padx=10, pady=(10,4))
        tk.Label(sf, text="Pontuação de Autenticidade",
                 font=("Courier New", 9), fg=MUTED, bg=BG3).pack(anchor="w")
        tk.Label(sf, text=f"{score} / 100",
                 font=("Courier New", 26, "bold"), fg=color, bg=BG3).pack(anchor="w")
        nivel = "BAIXO ✅" if score >= 80 else ("MÉDIO ⚠️" if score >= 50 else "ALTO 🚨")
        tk.Label(sf, text=f"Nível de Risco: {nivel}",
                 font=("Courier New", 11, "bold"), fg=color, bg=BG3).pack(anchor="w")

        tk.Label(self.auth_inner, text="Verificações:",
                 font=("Courier New", 9, "bold"), fg=ACCENT3, bg=BG2).pack(anchor="w", padx=12, pady=(8,2))
        for chk in checks:
            row = tk.Frame(self.auth_inner, bg=BG2)
            row.pack(fill="x", padx=12, pady=1)
            ic = "✅" if chk["ok"] else "❌"
            c  = SUCCESS if chk["ok"] else DANGER
            tk.Label(row, text=f"{ic}  {chk['label']}",
                     font=("Courier New", 9), fg=c, bg=BG2, anchor="w").pack(side="left")
            tk.Label(row, text=chk.get("detail",""),
                     font=("Courier New", 8), fg=MUTED, bg=BG2, anchor="e").pack(side="right")
        if flags:
            tk.Label(self.auth_inner, text="⚠  Alertas:",
                     font=("Courier New", 9, "bold"), fg=WARNING, bg=BG2).pack(anchor="w", padx=12, pady=(10,2))
            for fl in flags:
                tk.Label(self.auth_inner, text=f"  ⚑  {fl}",
                         font=("Courier New", 8), fg=WARNING, bg=BG2, anchor="w").pack(anchor="w", padx=14)

    def _preencher_meta(self, decoded, analysis, tel=None):
        self.meta_text.configure(state="normal")
        self.meta_text.delete("1.0", "end")
        meta  = decoded.get("metadata", {})
        lines = []
        lines.append("═"*60)
        lines.append("  METADADOS TRIANGULADOS — PixieCat")
        lines.append("═"*60)

        # CEP enriquecido pela telemetria
        cep_display = meta.get("cep","—")
        cidade_display = meta.get("cidade","—")
        estado_display = ""
        regiao_display = ""
        logradouro_display = ""
        bairro_display = ""
        ddd_display = ""
        ibge_display = ""
        cep_fonte = "Payload EMV"

        if tel and tel.cep_triangulado:
            ct = tel.cep_triangulado
            if ct.cep:        cep_display       = f"{ct.cep[:5]}-{ct.cep[5:]}" if len(ct.cep)==8 else ct.cep
            if ct.cidade:     cidade_display     = ct.cidade
            if ct.estado:     estado_display     = ct.estado
            if ct.regiao:     regiao_display     = ct.regiao
            if ct.logradouro: logradouro_display = ct.logradouro
            if ct.bairro:     bairro_display     = ct.bairro
            if ct.ddd:        ddd_display        = ct.ddd
            if ct.ibge:       ibge_display       = ct.ibge
            cep_fonte = f"{ct.fonte} (consenso: {'✓' if tel.cep_consenso else '~'})"

        sections = [
            ("RECEPTOR (Beneficiário)", [
                ("Nome",             meta.get("nome","—")),
                ("Chave Pix",        meta.get("chave","—")),
                ("Tipo de Chave",    meta.get("tipo_chave","—")),
                ("Banco / PSP",      meta.get("banco","—")),
            ]),
            ("LOCALIZAÇÃO (Triangulada)", [
                ("CEP",              cep_display),
                ("Logradouro",       logradouro_display or "—"),
                ("Bairro",           bairro_display     or "—"),
                ("Cidade",           cidade_display),
                ("Estado",           estado_display     or "—"),
                ("Região",           regiao_display     or "—"),
                ("DDD",              ddd_display        or "—"),
                ("Código IBGE",      ibge_display       or "—"),
                ("Fonte CEP",        cep_fonte),
            ]),
            ("TRANSAÇÃO", [
                ("Valor",            meta.get("valor","Não especificado")),
                ("Moeda",            meta.get("moeda","BRL")),
                ("TxID",             meta.get("txid","—")),
                ("Descrição",        meta.get("descricao","—")),
                ("URL Payload",      meta.get("url","—")),
            ]),
            ("INTEGRIDADE", [
                ("CRC-16 calculado", decoded.get("crc_calculated","—")),
                ("CRC-16 payload",   decoded.get("crc_payload","—")),
                ("CRC válido",       "✅ SIM" if decoded.get("crc_valid") else "❌ NÃO"),
                ("Formato",          decoded.get("format","—")),
                ("Versão EMV",       decoded.get("version","—")),
            ]),
            ("RISCO", [
                ("Score",            f"{analysis.get('score','—')}/100"),
                ("Nível",            analysis.get("nivel","—")),
                ("Alertas",          str(len(analysis.get("flags",[])))),
            ]),
        ]
        for title, rows in sections:
            lines.append("")
            lines.append(f"┌─ {title} " + "─"*(54-len(title)))
            for k,v in rows:
                lines.append(f"│  {k:<22} {v}")
            lines.append("└" + "─"*59)

        if tel and tel.anomalias:
            lines.append("")
            lines.append("⚠  ANOMALIAS DETECTADAS PELA TELEMETRIA:")
            for a in tel.anomalias:
                lines.append(f"   ⚑  {a}")

        if analysis.get("flags"):
            lines.append("")
            lines.append("⚠  ALERTAS DE AUTENTICIDADE:")
            for fl in analysis["flags"]:
                lines.append(f"   ⚑  {fl}")

        lines.append("")
        lines.append("═"*60)
        self.meta_text.insert("end", "\n".join(lines))
        self.meta_text.configure(state="disabled")

    def _preencher_tel(self, tel: TelemetryReport):
        # ── CEP ──
        self.tel_cep_text.configure(state="normal")
        self.tel_cep_text.delete("1.0", "end")
        lines = ["═"*55, "  TRIANGULAÇÃO DE CEP — 3 Fontes Independentes", "═"*55, ""]

        if tel.cep_payload:
            lines.append(f"CEP do payload EMV (campo 61): {tel.cep_payload}")
        else:
            lines.append("CEP do payload EMV: Ausente no payload")

        lines.append(f"Consenso entre fontes: {'✅ SIM' if tel.cep_consenso else '⚠ PARCIAL'}")
        lines.append("")

        for r in tel.cep_fontes:
            lines.append(f"┌─ {r.fonte} (confiança {r.confianca}% · {r.latencia_ms:.0f}ms)")
            lines.append(f"│  CEP:        {r.cep}")
            lines.append(f"│  Logradouro: {r.logradouro or '—'}")
            lines.append(f"│  Bairro:     {r.bairro or '—'}")
            lines.append(f"│  Cidade:     {r.cidade}")
            lines.append(f"│  Estado:     {r.estado} — {r.regiao}")
            lines.append(f"│  DDD:        {r.ddd or '—'}")
            lines.append(f"│  IBGE:       {r.ibge or '—'}")
            lines.append("└" + "─"*50)
            lines.append("")

        if tel.cep_triangulado:
            ct = tel.cep_triangulado
            lines.append("★  RESULTADO TRIANGULADO (melhor consenso)")
            lines.append(f"   CEP:        {ct.cep}")
            lines.append(f"   Endereço:   {ct.logradouro or '—'}, {ct.bairro or '—'}")
            lines.append(f"   Cidade/UF:  {ct.cidade} / {ct.estado} ({ct.regiao})")
            lines.append(f"   DDD / IBGE: {ct.ddd or '—'} / {ct.ibge or '—'}")
        else:
            lines.append("ℹ  Nenhum CEP pôde ser triangulado.")
            lines.append("   (payload sem campo 61 e chave sem DDD inferível)")

        self.tel_cep_text.insert("end", "\n".join(lines))
        self.tel_cep_text.configure(state="disabled")

        # ── Rede / DNS / TLS ──
        self.tel_net_text.configure(state="normal")
        self.tel_net_text.delete("1.0", "end")
        net_lines = ["═"*55, "  DNS · TLS · HTTP PROBE", "═"*55, ""]

        dns = tel.dns
        if dns:
            net_lines.append(f"┌─ DNS")
            net_lines.append(f"│  Hostname: {dns.hostname}")
            net_lines.append(f"│  IPs:      {', '.join(dns.ips) or '—'}")
            net_lines.append(f"│  rDNS:     {', '.join(dns.rdns) or 'Sem resolução reversa'}")
            net_lines.append(f"│  Latência: {dns.latencia_ms:.0f}ms")
            net_lines.append("└" + "─"*50)
            net_lines.append("")

        http = tel.http_probe
        if http:
            net_lines.append(f"┌─ HTTP Probe")
            net_lines.append(f"│  URL:          {http.url[:60]}")
            net_lines.append(f"│  Status HTTP:  {http.status}")
            net_lines.append(f"│  Servidor:     {http.server or '—'}")
            net_lines.append(f"│  X-Powered-By: {http.x_powered_by or '—'}")
            net_lines.append(f"│  Redirects:    {len(http.redirects)}")
            for rd in http.redirects:
                net_lines.append(f"│    → {rd[:70]}")
            net_lines.append(f"│  Latência:     {http.latencia_ms:.0f}ms")
            net_lines.append(f"│  Suspeito:     {'⚠ SIM — ' + http.motivo_suspeito if http.suspeito else '✅ NÃO'}")
            net_lines.append("└" + "─"*50)
            net_lines.append("")
            if http.tls_version:
                net_lines.append(f"┌─ TLS / Certificado")
                net_lines.append(f"│  Versão TLS:  {http.tls_version}")
                net_lines.append(f"│  Cipher:      {http.tls_cipher}")
                net_lines.append(f"│  Emissor:     {http.tls_issuer or '—'}")
                net_lines.append(f"│  Validade:    {http.tls_expiry or '—'}")
                net_lines.append("└" + "─"*50)

        psp = tel.psp
        if psp:
            net_lines.append("")
            net_lines.append(f"┌─ PSP / Banco Identificado")
            net_lines.append(f"│  Nome:   {psp.get('nome','—')}")
            net_lines.append(f"│  ISPB:   {psp.get('ispb','—')}")
            net_lines.append(f"│  Tipo:   {psp.get('tipo','—')}")
            net_lines.append(f"│  Cidade: {psp.get('cidade','—')} / {psp.get('estado','—')}")
            net_lines.append("└" + "─"*50)

        if not dns and not http:
            net_lines.append("ℹ  Análise de rede disponível apenas para payloads dinâmicos (com URL).")

        self.tel_net_text.insert("end", "\n".join(net_lines))
        self.tel_net_text.configure(state="disabled")

        # ── GeoIP ──
        self.tel_geo_text.configure(state="normal")
        self.tel_geo_text.delete("1.0", "end")
        geo = tel.geo_ip
        geo_lines = ["═"*55, "  GEOLOCALIZAÇÃO DO HOST (ip-api.com)", "═"*55, ""]
        if geo.get("status") == "success":
            geo_lines.append(f"IP:            {geo.get('query','—')}")
            geo_lines.append(f"País:          {geo.get('country','—')} ({geo.get('countryCode','—')})")
            geo_lines.append(f"Estado/Região: {geo.get('regionName','—')}")
            geo_lines.append(f"Cidade:        {geo.get('city','—')}")
            geo_lines.append(f"CEP local:     {geo.get('zip','—')}")
            geo_lines.append(f"Coordenadas:   {geo.get('lat','—')}, {geo.get('lon','—')}")
            geo_lines.append(f"ISP:           {geo.get('isp','—')}")
            geo_lines.append(f"Organização:   {geo.get('org','—')}")
            geo_lines.append(f"AS:            {geo.get('as','—')}")
            geo_lines.append(f"Latência:      {geo.get('latencia_ms',0):.0f}ms")
            if geo.get("countryCode","BR") != "BR":
                geo_lines.append("")
                geo_lines.append("🚨 ALERTA: Host fora do Brasil!")
        else:
            geo_lines.append("ℹ  GeoIP disponível apenas para payloads dinâmicos (com URL).")
        self.tel_geo_text.insert("end", "\n".join(geo_lines))
        self.tel_geo_text.configure(state="disabled")

        # ── Anomalias ──
        self.tel_anom_text.configure(state="normal")
        self.tel_anom_text.delete("1.0", "end")
        anom_lines = ["═"*55, "  ANOMALIAS DETECTADAS PELA TELEMETRIA", "═"*55, ""]
        anom_lines.append(f"Sessão:       {tel.session_id}")
        anom_lines.append(f"Duração:      {tel.duracao_total_ms:.0f}ms")
        anom_lines.append(f"Score delta:  {tel.score_delta:+d}")
        anom_lines.append("")
        if tel.anomalias:
            for i, a in enumerate(tel.anomalias, 1):
                anom_lines.append(f"⚑  [{i:02d}] {a}")
        else:
            anom_lines.append("✅  Nenhuma anomalia detectada pela telemetria.")
        self.tel_anom_text.insert("end", "\n".join(anom_lines))
        self.tel_anom_text.configure(state="disabled")

    # ── PDF ───────────────────────────────────────────────────────────

    def _gerar_pdf(self):
        if not self._last_result:
            messagebox.showwarning("PixieCat", "Realize uma análise antes de gerar o relatório.")
            return
        path = filedialog.asksaveasfilename(
            title="Salvar Relatório PDF",
            defaultextension=".pdf",
            filetypes=[("PDF","*.pdf")],
            initialfile="relatorio_pix_pixiecat.pdf",
        )
        if not path:
            return
        self._log(f"[>>] Gerando PDF: {path}")
        self._status("📄  Gerando PDF…")
        try:
            result = dict(self._last_result)
            result["tel_report"] = self._tel_report
            self.reporter.generate(result, path)
            self._log(f"[OK] PDF salvo: {path}")
            self._status(f"✅  PDF salvo: {path}")
            messagebox.showinfo("PixieCat", f"Relatório salvo!\n{path}")
        except Exception as e:
            self._log(f"[!!] PDF: {e}")
            messagebox.showerror("Erro", f"Falha ao gerar PDF:\n{e}")

    def _copiar(self):
        if not self._last_result:
            return
        self.clipboard_clear()
        self.clipboard_append(self.meta_text.get("1.0","end"))
        self._status("📋  Resultado copiado")

    def _limpar(self):
        self.entry_pix.delete("1.0","end")
        for row in self.tree_decode.get_children():
            self.tree_decode.delete(row)
        for w in self.auth_inner.winfo_children():
            w.destroy()
        for wid in (self.meta_text, self.tel_cep_text, self.tel_net_text,
                    self.tel_geo_text, self.tel_anom_text):
            wid.configure(state="normal")
            wid.delete("1.0","end")
            wid.configure(state="disabled")
        self._last_result = None
        self._tel_report  = None
        self._tel_status("Aguardando análise com telemetria…")
        self._status("Aguardando link Pix…")

    def _limpar_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0","end")
        self.log_text.configure(state="disabled")

    # ── Helpers ───────────────────────────────────────────────────────

    def _log(self, msg: str):
        import datetime
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"[{ts}] {msg}\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _status(self, msg: str, error: bool = False, warn: bool = False):
        self._status_var.set(msg)

    def _tel_status(self, msg: str):
        self._tel_status_var.set(msg)
        color = MUTED
        if "✅" in msg:   color = SUCCESS
        elif "⏳" in msg: color = WARNING
        elif "🚨" in msg: color = DANGER
        self._tel_status_lbl.configure(fg=color)

    def _status_score(self, score: int):
        if score >= 80:
            self._status(f"✅  Risco BAIXO ({score}/100)")
        elif score >= 50:
            self._status(f"⚠️   Risco MÉDIO ({score}/100)")
        else:
            self._status(f"🚨  Risco ALTO ({score}/100)")

    def _center(self):
        self.update_idletasks()
        w, h = 980, 740
        x = (self.winfo_screenwidth()  - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _on_close(self):
        self.telemetry.shutdown()
        self.destroy()


if __name__ == "__main__":
    app = PixieCatApp()
    app.mainloop()
