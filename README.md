# 🐱 PixieCat v1.1.01
### Decodificador & Analisador de Links Pix Anti-Golpe
**Created by psyhusk**

---

## O que é

PixieCat é uma ferramenta de segurança com interface gráfica para **decodificação e análise de autenticidade de links/QR Codes Pix**, ajudando o usuário a identificar possíveis golpes antes de realizar uma transferência.

---

## Funcionalidades

| Módulo | Descrição |
|--------|-----------|
| `pix_decoder.py` | Parser EMV/BR Code completo — decodifica todos os campos TLV do payload Pix |
| `pix_analyzer.py` | 12 verificações de autenticidade com score 0–100 |
| `pix_reporter.py` | Gerador de relatório PDF no padrão CyberSec (CERT.br / ISO 27035) |
| `pix_ui.py` | Componentes de interface reutilizáveis |
| `pix_config.py` | Gerenciador de configurações em `~/.pixiecat/config.json` |

---

## Requisitos

```bash
pip install reportlab Pillow
# tkinter geralmente já vem com Python
# Arch: sudo pacman -S tk python-pillow
# Debian/Ubuntu: sudo apt install python3-tk
```

---

## Como usar

### Modo direto
```bash
python PixieCat.py
```

### Instalar (GUI)
```bash
python pixiecat_installer.py
# Após: pixiecat   (no terminal)
```

### Build (executável standalone)
```bash
python build_pixiecat.py
# Executável em: dist/PixieCat
```

---

## Estrutura do projeto

```
pixiecat/
├── PixieCat.py              # Aplicação principal (GUI tkinter)
├── pixiecat_installer.py    # Installer com GUI animada
├── build_pixiecat.py        # Build script (PyInstaller)
├── modules/
│   ├── __init__.py
│   ├── pix_decoder.py       # Decodificador EMV/BR Code
│   ├── pix_analyzer.py      # Analisador de autenticidade
│   ├── pix_reporter.py      # Gerador de PDF CyberSec
│   ├── pix_ui.py            # Componentes de UI
│   └── pix_config.py        # Gerenciador de config
└── README.md
```

---

## O relatório PDF inclui

1. **Sumário executivo** com score colorido e análise narrativa
2. **Dados do payload** — metadados extraídos e payload bruto
3. **Análise de integridade** — CRC-16, campos EMV
4. **Checklist de autenticidade** — 12 verificações detalhadas
5. **Alertas e IoCs** — Indicadores de Comprometimento
6. **Recomendações** — orientadas pelo nível de risco
7. **Informações técnicas** — hash SHA-256, normas, algoritmos
8. **Disclaimer** legal

---

## Verificações realizadas

- ✅ CRC-16/CCITT (integridade do payload)
- ✅ Formato EMV correto (000201)
- ✅ Nome do beneficiário presente e válido
- ✅ Nome não está em lista de suspeitos
- ✅ Chave Pix identificada (CPF/CNPJ/e-mail/telefone/EVP)
- ✅ CPF com dígito verificador válido
- ✅ CNPJ com dígito verificador válido
- ✅ Valor da transação dentro do limite aceitável
- ✅ URL do payload em domínio oficial Pix
- ✅ Código de país = BR
- ✅ Moeda = BRL (986)
- ✅ GUI = br.gov.bcb.pix
- ✅ Comprimento mínimo do payload

---

*PixieCat não armazena nem transmite dados analisados. Uso exclusivamente educativo e preventivo.*
