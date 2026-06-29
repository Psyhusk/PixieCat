#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════╗
║   PixieCat — Build Script  (PyInstaller)                            ║
║   Gera executável único: gato violeta + ícone segurança             ║
║                                                                      ║
║   Uso:                                                               ║
║     python build_pixiecat.py                                         ║
║     python build_pixiecat.py --clean-only                            ║
║     python build_pixiecat.py --icon-only                             ║
║                                                                      ║
║   Pré-requisitos:                                                    ║
║     pip install pyinstaller Pillow reportlab                         ║
║     Arch: sudo pacman -S python-pyinstaller python-pillow            ║
║                                                                      ║
║   Created by psyhusk                                                 ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import subprocess, sys, os, shutil, math, platform
from pathlib import Path

# ── Config do build ───────────────────────────────────────────────────
APP_NAME         = "PixieCat"
INSTALLER_SCRIPT = "pixiecat_installer.py"
MAIN_SCRIPT      = "PixieCat.py"
MODULES_DIR      = "modules"
VERSION          = "1.0.0"
ICON_PNG         = "pixiecat_icon.png"


def _is_arch() -> bool:
    try:
        return Path("/etc/arch-release").exists()
    except Exception:
        return False


def check_pyinstaller() -> bool:
    try:
        import PyInstaller
        print(f"[+] PyInstaller {PyInstaller.__version__} disponível.")
        return True
    except ImportError:
        print("[*] Instalando PyInstaller…")
        flags = ["--break-system-packages"] if _is_arch() else []
        r = subprocess.run(
            [sys.executable, "-m", "pip", "install", "pyinstaller"] + flags,
            capture_output=True, text=True
        )
        if r.returncode == 0:
            print("[+] PyInstaller instalado.")
            return True
        print(f"[-] Falha: {r.stderr[:200]}")
        return False


def generate_icon() -> str | None:
    """
    Gera ícone PNG 256×256: gato com olhos violeta + escudo de segurança.
    """
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        print("[*] Instalando Pillow…")
        flags = ["--break-system-packages"] if _is_arch() else []
        subprocess.run([sys.executable, "-m", "pip", "install", "Pillow"] + flags,
                       capture_output=True)
        try:
            from PIL import Image, ImageDraw
        except ImportError:
            print("[!] Pillow indisponível — build sem ícone.")
            return None

    print("[*] Gerando ícone PixieCat (256×256)…")
    SIZE = 256
    img  = Image.new("RGBA", (SIZE, SIZE), (5, 3, 8, 255))
    d    = ImageDraw.Draw(img)

    # Paleta violeta
    V1   = (124, 58, 237)    # GLOW1
    V2   = (168, 85, 247)    # GLOW2
    V3   = (192, 132, 252)   # GLOW3
    DARK = (13,  10,  24)
    DBRDR= (76,  29, 149)
    DARKR= (8,   5,  16)

    cx, cy = SIZE // 2, SIZE // 2 - 10

    # Círculo externo
    d.ellipse([4, 4, SIZE - 4, SIZE - 4], outline=V1, width=2)
    d.ellipse([8, 8, SIZE - 8, SIZE - 8], outline=(50, 20, 100), width=1)

    # Corpo
    d.ellipse([cx - 48, cy + 6, cx + 48, cy + 66],
               fill=DARKR, outline=V1, width=1)
    # Cauda
    d.arc([cx + 26, cy + 24, cx + 78, cy + 82],
           start=0, end=210, fill=V1, width=2)
    # Cabeça
    d.ellipse([cx - 56, cy - 120, cx + 56, cy - 4],
               fill=DARK, outline=V1, width=2)
    # Orelhas
    d.polygon([cx - 56, cy - 70, cx - 80, cy - 148, cx - 20, cy - 92],
               fill=(20, 8, 40), outline=V1)
    d.polygon([cx + 56, cy - 70, cx + 80, cy - 148, cx + 20, cy - 92],
               fill=(20, 8, 40), outline=V1)
    # Olhos violeta (o destaque)
    for ex in [cx - 20, cx + 20]:
        d.ellipse([ex - 13, cy - 70, ex + 13, cy - 44],
                   fill=(20, 5, 40), outline=V2, width=2)
        d.ellipse([ex - 9,  cy - 67, ex + 9,  cy - 47], fill=V1)
        d.ellipse([ex - 4,  cy - 65, ex + 4,  cy - 49], fill=(0, 0, 0))
        d.ellipse([ex - 8,  cy - 66, ex - 3,  cy - 60], fill=V3)

    # Nariz e boca
    d.polygon([cx - 5, cy - 26, cx + 5, cy - 26, cx, cy - 18], fill=DBRDR)
    d.line([cx, cy - 18, cx - 6, cy - 11, cx - 13, cy - 8], fill=DBRDR, width=1)
    d.line([cx, cy - 18, cx + 6, cy - 11, cx + 13, cy - 8], fill=DBRDR, width=1)
    # Bigodes
    for dy in [-4, -1, 2]:
        d.line([cx - 48, cy - 28 + dy, cx - 10, cy - 28 + dy], fill=DBRDR, width=1)
        d.line([cx + 10, cy - 28 + dy, cx + 48, cy - 28 + dy], fill=DBRDR, width=1)

    # Escudo de segurança (substituindo pentagrama — temática CyberSec)
    sx, sy, sr = cx, cy + 118, 34
    shield = [
        (sx,          sy - sr),
        (sx + sr,     sy - sr // 2),
        (sx + sr,     sy + sr // 3),
        (sx,          sy + sr),
        (sx - sr,     sy + sr // 3),
        (sx - sr,     sy - sr // 2),
    ]
    d.polygon(shield, fill=(20, 8, 40), outline=V1)
    d.ellipse([sx - sr - 4, sy - sr - 4, sx + sr + 4, sy + sr + 4],
               outline=V2, width=1)
    # Check mark no escudo
    d.line([sx - 10, sy + 2, sx - 2, sy + 12, sx + 14, sy - 10],
            fill=V2, width=3)

    img.save(ICON_PNG, format="PNG")
    print(f"[+] Ícone salvo: {ICON_PNG}")

    if platform.system() == "Windows":
        ico = "pixiecat.ico"
        img.save(ico, format="ICO",
                 sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)])
        print(f"[+] ICO: {ico}")
        return ico

    return ICON_PNG


def check_scripts() -> bool:
    ok = True
    required = [INSTALLER_SCRIPT, MAIN_SCRIPT]
    for f in required:
        if Path(f).exists():
            print(f"[+] Encontrado: {f}")
        else:
            print(f"[-] FALTANDO: {f}")
            ok = False
    if not Path(MODULES_DIR).exists():
        print(f"[-] FALTANDO: diretório {MODULES_DIR}/")
        ok = False
    else:
        print(f"[+] Encontrado: {MODULES_DIR}/")
    return ok


def build():
    print()
    print("=" * 68)
    print(f"  {APP_NAME}  v{VERSION}  —  Analisador de Links Pix Anti-Golpe")
    print("  Build Script · PyInstaller · psyhusk")
    print("=" * 68)
    print()

    plat = platform.system()
    arch = platform.machine()
    print(f"[i] Plataforma : {plat} {arch}")
    print(f"[i] Python     : {sys.version.split()[0]}")
    if _is_arch():
        print("[i] Arch Linux detectado — usando --break-system-packages")
    print()

    if not check_pyinstaller():
        sys.exit(1)

    if not check_scripts():
        print(f"\n[-] Organize os arquivos e tente novamente.")
        sys.exit(1)

    icon_path = generate_icon()

    sep = os.pathsep
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        "--name",  APP_NAME,
        "--clean",
        "--noconfirm",
    ]

    if icon_path and Path(icon_path).exists():
        cmd += ["--icon", icon_path]

    # Inclui o script principal e o diretório de módulos
    cmd += ["--add-data", f"{MAIN_SCRIPT}{sep}."]
    cmd += ["--add-data", f"{MODULES_DIR}{sep}{MODULES_DIR}"]

    hidden = [
        "tkinter", "tkinter.font", "tkinter.messagebox",
        "tkinter.ttk", "tkinter.scrolledtext", "tkinter.filedialog",
        "reportlab", "reportlab.lib", "reportlab.platypus",
        "reportlab.pdfgen", "reportlab.lib.styles",
        "reportlab.lib.pagesizes", "reportlab.lib.units",
        "reportlab.lib.colors", "reportlab.lib.enums",
        "Pillow", "PIL", "PIL.Image", "PIL.ImageDraw",
        "pathlib", "hashlib", "threading", "subprocess",
        "shutil", "json", "re", "math", "struct",
        "datetime", "socket", "platform", "urllib",
        "urllib.request", "urllib.parse", "urllib.error",
        # módulos internos do PixieCat
        "modules.pix_decoder",
        "modules.pix_analyzer",
        "modules.pix_reporter",
        "modules.pix_ui",
        "modules.pix_config",
    ]
    for hi in hidden:
        cmd += ["--hidden-import", hi]

    cmd += [
        "--collect-submodules", "reportlab",
        "--collect-data",       "reportlab",
    ]

    cmd.append(INSTALLER_SCRIPT)

    print(f"\n[>] Iniciando PyInstaller…")
    print(f"    Entry:   {INSTALLER_SCRIPT}")
    print(f"    Bundle:  {MAIN_SCRIPT} + {MODULES_DIR}/")
    print(f"    Output:  dist/{APP_NAME}")
    if _is_arch():
        print("    Nota:    Wayland → use  GDK_BACKEND=x11 ./PixieCat")
    print()

    result = subprocess.run(cmd, text=True)

    if result.returncode == 0:
        print()
        print("=" * 68)
        print("  BUILD CONCLUÍDO COM SUCESSO!")
        print("=" * 68)
        ext = ".exe" if platform.system() == "Windows" else ""
        exe = Path("dist") / f"{APP_NAME}{ext}"
        if exe.exists():
            size = exe.stat().st_size / 1024 / 1024
            print(f"\n  Executável : {exe}")
            print(f"  Tamanho    : {size:.1f} MB")
            print(f"  Plataforma : {platform.system()} {platform.machine()}")
        print()
        print("  Para executar:")
        print(f"    ./dist/{APP_NAME}                          (Linux/Arch)")
        print(f"    GDK_BACKEND=x11 ./dist/{APP_NAME}         (Wayland)")
        print(f"    dist\\{APP_NAME}.exe                        (Windows)")
        print()
        print("  Para instalar:")
        print(f"    ./dist/{APP_NAME}   (abre o installer GUI)")
        print()
    else:
        print("\n[-] BUILD FALHOU.")
        print("    Verifique os erros acima.")
        print()
        print("  Dicas:")
        print("    pip install pyinstaller Pillow reportlab")
        if _is_arch():
            print("    sudo pacman -S tk python-pillow")
        else:
            print("    sudo apt install python3-tk python3-dev")
        sys.exit(1)


def clean():
    for item in [f"{APP_NAME}.spec", "build", ICON_PNG]:
        p = Path(item)
        if p.exists():
            shutil.rmtree(p) if p.is_dir() else p.unlink()
            print(f"[*] Removido: {item}")
    print("[*] Limpeza concluída.")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(
        description=f"Build Script — {APP_NAME} v{VERSION} — psyhusk"
    )
    ap.add_argument("--clean-only", action="store_true",
                    help="Apenas remove artefatos de builds anteriores")
    ap.add_argument("--icon-only",  action="store_true",
                    help="Apenas gera o ícone PNG/ICO")
    args = ap.parse_args()

    if args.clean_only:
        clean()
    elif args.icon_only:
        generate_icon()
    else:
        build()
        clean()
