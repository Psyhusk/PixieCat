#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════╗
║   PixieCat  v1.0.0  —  Installer                                    ║
║   Analisador de Links Pix Anti-Golpe                                ║
║   Frameless · Animado · Interface em Português                      ║
║                                                                      ║
║   Created by psyhusk                                                 ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import os, sys, subprocess, threading, shutil, time, math
from pathlib import Path

try:
    import tkinter as tk
except ImportError:
    print("[!] tkinter ausente.")
    print("    Arch:   sudo pacman -S tk")
    print("    Debian: sudo apt install python3-tk")
    sys.exit(1)

# ── Paleta violeta ────────────────────────────────────────────────────
BG      = "#050308"
BG2     = "#080510"
BG3     = "#0d0a18"
GLOW1   = "#7c3aed"
GLOW2   = "#a855f7"
GLOW3   = "#c084fc"
BORDER  = "#4c1d95"
TEXT    = "#ede9fe"
MUTED   = "#7c6fa0"
DIM     = "#3d3560"
SUCCESS = "#22c55e"
DANGER  = "#ef4444"
WARNING = "#f59e0b"
MONO    = "#c4b5fd"

VERSION      = "1.0.0"
NAME         = "PixieCat"
INSTALL_DIR  = Path.home() / ".local" / "share" / "pixiecat"
BIN_DIR      = Path.home() / ".local" / "bin"
CONFIG_DIR   = Path.home() / ".pixiecat"
DESKTOP_FILE = Path.home() / ".local" / "share" / "applications" / "pixiecat.desktop"
MAIN_SCRIPT  = "PixieCat.py"
MODULES_DIR  = "modules"


def _is_arch() -> bool:
    try:
        return Path("/etc/arch-release").exists()
    except Exception:
        return False


def run_cmd(cmd: str, timeout: int = 90):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True,
                           text=True, timeout=timeout)
        return r.returncode == 0, (r.stdout + r.stderr).strip()
    except Exception as e:
        return False, str(e)


def do_install(log_cb, prog_cb, done_cb):
    errors = []

    def step(pct, msg, fn=None):
        log_cb(f"[>>] {msg}")
        if fn:
            ok, out = fn()
            if not ok:
                log_cb(f"[!!] {out[:120] if out else 'Falhou'}")
                errors.append(msg)
            else:
                if out:
                    log_cb(f"     {out[:80]}")
        prog_cb(pct, msg)
        time.sleep(0.35)

    flags = "--break-system-packages" if _is_arch() else ""
    pip   = lambda pkg: f"{sys.executable} -m pip install {pkg} --quiet {flags}"

    step(5,  "Verificando Python 3.8+",
         lambda: (sys.version_info >= (3, 8), sys.version))

    step(15, "Instalando reportlab (gerador PDF)",
         lambda: run_cmd(pip("reportlab")))
    log_cb("// reportlab instalado. Relatórios CyberSec prontos para emissão.")

    step(25, "Instalando Pillow (ícones e gráficos)",
         lambda: run_cmd(pip("Pillow")))
    log_cb("// Pillow disponível. Ícone do gato renderizado.")

    step(35, "Verificando tkinter",
         lambda: (True, f"tkinter {tk.TkVersion} OK"))

    # Criar diretórios
    log_cb("[>>] Criando diretórios…")
    INSTALL_DIR.mkdir(parents=True, exist_ok=True)
    (INSTALL_DIR / "modules").mkdir(exist_ok=True)
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    prog_cb(45, "Diretórios criados")
    time.sleep(0.3)

    # Copiar script principal
    log_cb("[>>] Copiando PixieCat.py…")
    src = Path(__file__).parent / MAIN_SCRIPT
    if src.exists():
        shutil.copy2(src, INSTALL_DIR / MAIN_SCRIPT)
        log_cb(f"     {src} → {INSTALL_DIR / MAIN_SCRIPT}")
    else:
        log_cb(f"[!!] {MAIN_SCRIPT} não encontrado!")
        errors.append("Script principal ausente")

    # Copiar módulos
    log_cb("[>>] Copiando módulos…")
    src_mods = Path(__file__).parent / MODULES_DIR
    if src_mods.exists():
        for f in src_mods.iterdir():
            if f.suffix == ".py":
                shutil.copy2(f, INSTALL_DIR / "modules" / f.name)
                log_cb(f"     módulo copiado: {f.name}")
    else:
        log_cb(f"[!!] Diretório modules/ não encontrado!")
        errors.append("Módulos ausentes")
    prog_cb(62, "Arquivos copiados")
    time.sleep(0.3)

    # Config padrão
    import json
    cfg_file = CONFIG_DIR / "config.json"
    if not cfg_file.exists():
        log_cb("[>>] Criando config padrão em ~/.pixiecat/config.json…")
        cfg_file.write_text(json.dumps({
            "tema":             "violeta",
            "salvar_historico": True,
            "dir_relatorios":   str(Path.home() / "Documentos"),
            "version":          VERSION,
            "author":           "psyhusk",
        }, indent=2, ensure_ascii=False))
        log_cb(f"     Criado: {cfg_file}")
    else:
        log_cb("     Config existente mantida.")
    prog_cb(70, "Config criada")
    log_cb("// Config salva. Preferências preservadas entre sessões.")
    time.sleep(0.3)

    # Launcher shell
    log_cb("[>>] Criando launcher ~/.local/bin/pixiecat…")
    BIN_DIR.mkdir(parents=True, exist_ok=True)
    launcher = BIN_DIR / "pixiecat"
    launcher.write_text(
        f"#!/bin/bash\n"
        f"# PixieCat launcher — gerado pelo installer\n"
        f"exec {sys.executable} {INSTALL_DIR / MAIN_SCRIPT} \"$@\"\n"
    )
    launcher.chmod(0o755)
    log_cb(f"     Launcher: {launcher}")
    prog_cb(80, "Launcher criado")
    time.sleep(0.3)

    # .desktop entry
    log_cb("[>>] Criando entrada .desktop…")
    DESKTOP_FILE.parent.mkdir(parents=True, exist_ok=True)
    DESKTOP_FILE.write_text(
        f"[Desktop Entry]\n"
        f"Name=PixieCat {VERSION}\n"
        f"Comment=Analisador de Links Pix Anti-Golpe — psyhusk\n"
        f"Exec={sys.executable} {INSTALL_DIR / MAIN_SCRIPT}\n"
        f"Icon=security-high\n"
        f"Terminal=false\n"
        f"Type=Application\n"
        f"Categories=System;Security;Network;Utility;\n"
        f"Keywords=pix;segurança;golpe;fraude;qrcode;pagamento;\n"
        f"StartupNotify=true\n"
    )
    log_cb(f"     .desktop: {DESKTOP_FILE}")
    prog_cb(90, ".desktop criado")
    time.sleep(0.3)

    prog_cb(100, "Instalação concluída")
    log_cb("─" * 52)
    log_cb(f"✓ PixieCat instalado em {INSTALL_DIR}")
    log_cb(f"  Execute com: pixiecat  ou  python {INSTALL_DIR / MAIN_SCRIPT}")
    log_cb("─" * 52)
    done_cb(errors)


# ── Interface do Installer ────────────────────────────────────────────

class PixieCatInstaller(tk.Tk):

    W = 860
    H = 600

    def __init__(self):
        super().__init__()
        self.title(f"{NAME} {VERSION} — Installer")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.overrideredirect(True)   # frameless

        self._dx = self._dy = 0

        self._center()
        self._build()
        self._animate_glow()
        self._animate_cat()

    def _center(self):
        x = (self.winfo_screenwidth()  - self.W) // 2
        y = (self.winfo_screenheight() - self.H) // 2
        self.geometry(f"{self.W}x{self.H}+{x}+{y}")

    def _build(self):
        self.cv = tk.Canvas(self, width=self.W, height=self.H,
                            bg=BG, highlightthickness=0)
        self.cv.pack()

        # Borda animada
        self._border_item = self.cv.create_rectangle(
            2, 2, self.W - 2, self.H - 2,
            outline=GLOW1, width=2
        )

        # Arraste
        self.cv.bind("<ButtonPress-1>",   self._press)
        self.cv.bind("<B1-Motion>",       self._drag)

        # Fechar
        self.cv.create_text(self.W - 16, 14, text="✕",
                             font=("Courier New", 11, "bold"),
                             fill=MUTED, tags="close")
        self.cv.tag_bind("close", "<Button-1>", lambda e: self.destroy())

        # Título
        self.cv.create_text(30, 28, text="🐱 PixieCat",
                             font=("Courier New", 18, "bold"),
                             fill=GLOW2, anchor="w")
        self.cv.create_text(30, 50, text=f"v{VERSION}  —  Analisador de Links Pix Anti-Golpe",
                             font=("Courier New", 9), fill=MUTED, anchor="w")
        self.cv.create_text(30, 64, text="Created by psyhusk",
                             font=("Courier New", 8), fill=DIM, anchor="w")

        self.cv.create_line(0, 76, self.W, 76, fill=BORDER + "88", width=1)

        # Painel direito — gato animado
        self._draw_cat_panel()

        # Painel esquerdo — controles
        self._draw_control_panel()

    def _draw_cat_panel(self):
        PW = 260
        cx = self.W - PW // 2
        cy = 290

        self.cv.create_rectangle(self.W - PW, 76, self.W, self.H,
                                  fill=BG2, outline=BORDER + "55", width=1)
        self.cv.create_text(self.W - PW // 2, 100,
                             text="PixieCat", font=("Courier New", 13, "bold"),
                             fill=GLOW2)
        self.cv.create_text(self.W - PW // 2, 118,
                             text="Analisador Pix", font=("Courier New", 8),
                             fill=MUTED)

        # Gato desenhado com Canvas
        self._cat_items = []
        self._draw_cat(cx, cy)

        # Status lateral
        self._status_side = self.cv.create_text(
            self.W - PW // 2, self.H - 30,
            text="PRONTO", font=("Courier New", 9, "bold"), fill=GLOW1
        )

    def _draw_cat(self, cx, cy):
        c = self.cv
        # Corpo
        c.create_oval(cx - 38, cy + 10, cx + 38, cy + 65,
                       fill=BG3, outline=GLOW1, width=1)
        # Cauda
        c.create_arc(cx + 20, cy + 20, cx + 70, cy + 75,
                      start=0, extent=210, outline=GLOW1, width=2, style="arc")
        # Cabeça
        c.create_oval(cx - 44, cy - 90, cx + 44, cy + 8,
                       fill=BG3, outline=GLOW1, width=2)
        # Orelhas
        c.create_polygon(cx - 44, cy - 50, cx - 62, cy - 108, cx - 16, cy - 66,
                          fill=BG2, outline=GLOW1)
        c.create_polygon(cx + 44, cy - 50, cx + 62, cy - 108, cx + 16, cy - 66,
                          fill=BG2, outline=GLOW1)
        # Olhos violeta (animados)
        self._eye_items = []
        for ex in [cx - 15, cx + 15]:
            iris = c.create_oval(ex - 9, cy - 56, ex + 9, cy - 36,
                                  fill=GLOW1, outline=GLOW2, width=1)
            pupil = c.create_oval(ex - 4, cy - 54, ex + 4, cy - 38,
                                   fill="black")
            glow  = c.create_oval(ex - 8, cy - 55, ex - 3, cy - 48,
                                   fill=GLOW3)
            self._eye_items += [("iris", iris), ("glow", glow)]
        # Nariz e boca
        c.create_polygon(cx - 4, cy - 20, cx + 4, cy - 20, cx, cy - 13,
                          fill=BORDER)
        c.create_line(cx, cy - 13, cx - 5, cy - 7, cx - 10, cy - 4,
                       fill=BORDER, width=1)
        c.create_line(cx, cy - 13, cx + 5, cy - 7, cx + 10, cy - 4,
                       fill=BORDER, width=1)
        # Bigodes
        for dy in [-3, 0, 3]:
            c.create_line(cx - 38, cy - 18 + dy, cx - 8, cy - 18 + dy,
                           fill=DIM, width=1)
            c.create_line(cx + 8,  cy - 18 + dy, cx + 38, cy - 18 + dy,
                           fill=DIM, width=1)

    def _draw_control_panel(self):
        MW = self.W - 260

        # Destino
        self.cv.create_text(20, 94, text="Destino:",
                             font=("Courier New", 9), fill=MUTED, anchor="w")
        self.cv.create_text(88, 94, text=str(INSTALL_DIR),
                             font=("Courier New", 8, "bold"), fill=TEXT, anchor="w")

        # Componentes
        self.cv.create_text(20, 118, text="Componentes instalados:",
                             font=("Courier New", 10, "bold"), fill=GLOW2, anchor="w")
        items = [
            ("🔗", "Decodificador EMV / BR Code — parser completo"),
            ("🔍", "Analisador de autenticidade — 12 verificações"),
            ("📄", "Gerador de relatório PDF — padrão CyberSec"),
            ("🧬", "Triangulação de metadados Pix"),
            ("🐱", "Interface gráfica em Português"),
            ("⚙️",  "Config em ~/.pixiecat/config.json"),
        ]
        for i, (ic, desc) in enumerate(items):
            y = 140 + i * 24
            self.cv.create_text(22, y, text=ic,
                                 font=("Courier New", 10), fill=GLOW1, anchor="w")
            self.cv.create_text(46, y, text=desc,
                                 font=("Courier New", 8),  fill=MUTED,  anchor="w")

        # Barra de progresso
        self.cv.create_line(0, 306, MW, 306, fill=BORDER + "55", width=1)
        self.cv.create_text(20, 320, text="Progresso:",
                             font=("Courier New", 9), fill=MUTED, anchor="w")
        self.cv.create_rectangle(20, 332, MW - 22, 350,
                                  fill="#090418", outline=BORDER, width=1)
        self._prog_bar = self.cv.create_rectangle(20, 332, 20, 350,
                                                   fill=GLOW1, outline="")
        self._prog_pct = self.cv.create_text(MW // 2, 341, text="0%",
                                              font=("Courier New", 9, "bold"), fill=TEXT)
        self._status_text = self.cv.create_text(20, 358, text="Aguardando…",
                                                 font=("Courier New", 8), fill=MUTED, anchor="w")

        # Log
        self._log_frame = tk.Frame(self, bg=BG3)
        self._log_frame.place(x=18, y=372, width=MW - 36, height=158)
        self._log_txt = tk.Text(self._log_frame,
                                 bg="#040210", fg=MONO,
                                 font=("Courier New", 7.5), relief="flat", bd=0,
                                 state="disabled", wrap="word")
        sb = tk.Scrollbar(self._log_frame, orient="vertical",
                           command=self._log_txt.yview,
                           bg=BG, troughcolor=BG, activebackground=GLOW1,
                           relief="flat", bd=0)
        self._log_txt.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self._log_txt.pack(fill="both", expand=True)
        self.cv.create_rectangle(17, 371, MW - 17, 531, outline=BORDER, width=1)

        # Botões
        MW2 = MW - 260 if False else MW
        self._btn_install = tk.Button(self,
            text="▶  INSTALAR PIXIECAT",
            font=("Courier New", 11, "bold"),
            bg=GLOW1, fg="#fff",
            activebackground=BORDER, activeforeground="#fff",
            relief="flat", bd=0, cursor="hand2",
            command=self._start_install)
        self._btn_install.place(x=18, y=540, width=260, height=40)

        self._btn_launch = tk.Button(self,
            text="🚀  INICIAR PIXIECAT",
            font=("Courier New", 10, "bold"),
            bg="#0d0820", fg=MUTED,
            activebackground=BG3, activeforeground=TEXT,
            relief="flat", bd=0, cursor="arrow",
            state="disabled",
            command=self._launch)
        self._btn_launch.place(x=290, y=540, width=MW - 310, height=40)

    # ── Animações ────────────────────────────────────────────────────

    def _animate_glow(self):
        colors = [GLOW1, "#6d28d9", "#7c3aed", "#8b5cf6",
                  "#7c3aed", GLOW1, "#5b21b6", "#4c1d95", "#5b21b6", GLOW1]
        idx = [0]
        def tick():
            if not self.winfo_exists(): return
            self.cv.itemconfigure(self._border_item,
                                   outline=colors[idx[0] % len(colors)])
            idx[0] += 1
            self.after(110, tick)
        tick()

    def _animate_cat(self):
        purples = [GLOW1, "#6d28d9", "#8b5cf6", GLOW2, GLOW3, GLOW2, GLOW1]
        glows   = [GLOW3, "#ddd6fe", "#c4b5fd", GLOW3, GLOW2]
        idx = [0]
        def tick():
            if not self.winfo_exists(): return
            col  = purples[idx[0] % len(purples)]
            gcol = glows[idx[0] % len(glows)]
            for kind, it in self._eye_items:
                try:
                    if kind == "iris": self.cv.itemconfigure(it, fill=col)
                    if kind == "glow": self.cv.itemconfigure(it, fill=gcol)
                except: pass
            idx[0] += 1
            self.after(160, tick)
        tick()

    # ── Arraste ──────────────────────────────────────────────────────

    def _press(self, e):
        self._dx = e.x; self._dy = e.y

    def _drag(self, e):
        self.geometry(f"+{self.winfo_x() + e.x - self._dx}"
                      f"+{self.winfo_y() + e.y - self._dy}")

    # ── Log / Progresso ──────────────────────────────────────────────

    def _log(self, msg):
        def _do():
            self._log_txt.configure(state="normal")
            self._log_txt.insert("end", msg + "\n")
            self._log_txt.see("end")
            self._log_txt.configure(state="disabled")
        try: self._log_txt.after(0, _do)
        except: pass

    def _prog(self, pct, msg=""):
        MW = self.W - 260
        bar_w = int(pct / 100 * (MW - 40))
        def _do():
            self.cv.coords(self._prog_bar, 20, 332, 20 + bar_w, 350)
            self.cv.itemconfigure(self._prog_pct, text=f"{pct}%")
            if msg:
                self.cv.itemconfigure(self._status_text, text=msg[:70])
        try: self.cv.after(0, _do)
        except: pass

    def _done(self, errors):
        def _do():
            if errors:
                msg = f"⚠ Concluído com {len(errors)} aviso(s)"; col = WARNING
            else:
                msg = "✓ PixieCat instalado com sucesso!";        col = SUCCESS
            try:
                self.cv.itemconfigure(self._status_text, text=msg, fill=col)
                if self._status_side:
                    self.cv.itemconfigure(self._status_side,
                                           text="INSTALADO" + (" ⚠" if errors else " ✓"),
                                           fill=col)
            except: pass
            self._btn_install.configure(state="disabled", bg="#0d0820")
            self._btn_launch.configure(state="normal", bg=GLOW1, fg="#fff",
                                        activebackground=BORDER, cursor="hand2")
        try: self.cv.after(0, _do)
        except: pass

    def _start_install(self):
        self._btn_install.configure(state="disabled", text="Instalando…")
        self._log(f"◈ {NAME} — Iniciando instalação…")
        self._log(f"   Sistema: {'Arch Linux' if _is_arch() else 'Linux/Unix'}")
        self._log("─" * 50)
        threading.Thread(
            target=do_install,
            args=(self._log, self._prog, self._done),
            daemon=True
        ).start()

    def _launch(self):
        target = INSTALL_DIR / MAIN_SCRIPT
        if target.exists():
            import subprocess as sp
            sp.Popen([sys.executable, str(target)])
            self.after(800, self.destroy)
        else:
            self._log(f"[!] Não encontrado: {target}")
            self._log("    Execute o installer novamente.")


if __name__ == "__main__":
    app = PixieCatInstaller()
    app.mainloop()
