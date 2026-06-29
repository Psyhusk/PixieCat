#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
modules/pix_analyzer.py
Analisador de autenticidade e triangulação de metadados Pix.
Created by psyhusk
"""

import re
import hashlib
import datetime
from typing import Any


# ── Padrões suspeitos conhecidos ──────────────────────────────────────
SUSPICIOUS_NAMES = [
    "teste", "test", "fraude", "golpe", "falso", "fake",
    "admin", "suporte", "atendimento pix", "central pix",
    "banco do brasil falso", "itau", "itaú", "bradesco falso",
]

SUSPICIOUS_URLS = [
    r"bit\.ly", r"t\.co", r"goo\.gl", r"tinyurl",
    r"ow\.ly", r"shorturl", r"cutt\.ly",
    r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}",   # IP direto
    r"ngrok", r"localhost",
]

OFFICIAL_PIX_DOMAINS = [
    "pix.bcb.gov.br",
    "pix.bb.com.br",
    "pix.itau.com.br",
    "pix.bradesco.com.br",
    "pix.santander.com.br",
    "pix.caixa.gov.br",
    "nubank.com.br",
    "api.infinitepay.io",
    "pix.mercadopago.com",
]

VALID_MCC_CODES = {
    "0000": "Não especificado (genérico)",
    "5411": "Supermercado",
    "5912": "Farmácia",
    "5999": "Comércio variado",
    "7372": "Serviços de software",
    "8099": "Serviços de saúde",
    "8211": "Escola / Ensino",
    "5812": "Restaurante",
    "4111": "Transporte",
    "5311": "Loja de departamento",
    "7011": "Hotel / Hospedagem",
    "5732": "Eletrônica",
    "5661": "Calçados",
    "5621": "Vestuário feminino",
}

CPF_CNPJ_BLACKLIST = set()   # Pode ser populado com base de dados externos


class PixAnalyzer:
    """
    Analisa um payload Pix decodificado e retorna:
      - score (0–100): 100 = totalmente legítimo
      - flags: lista de alertas textuais
      - checks: lista de verificações detalhadas
      - nivel: BAIXO / MÉDIO / ALTO
    """

    def analyze(self, decoded: dict) -> dict[str, Any]:
        meta   = decoded.get("metadata", {})
        fields = decoded.get("fields", [])
        fmt    = decoded.get("format", "Estático")

        score   = 100
        flags   = []
        checks  = []

        # ── 1. CRC-16 ─────────────────────────────────────────────────
        crc_ok = decoded.get("crc_valid", False)
        score -= 0 if crc_ok else 30
        if not crc_ok:
            flags.append("CRC-16 inválido — payload adulterado ou corrompido")
        checks.append({
            "label":  "CRC-16 (integridade do payload)",
            "ok":     crc_ok,
            "detail": f"Calculado={decoded.get('crc_calculated','?')} / Payload={decoded.get('crc_payload','?')}",
        })

        # ── 2. Formato correto (começa com 000201) ────────────────────
        payload   = decoded.get("payload", "")
        fmt_ok    = payload.startswith("000201") or payload.startswith("000201".lower())
        score    -= 0 if fmt_ok else 10
        if not fmt_ok:
            flags.append("Payload não inicia com 000201 — formato EMV inválido")
        checks.append({
            "label":  "Indicador de formato EMV (000201)",
            "ok":     fmt_ok,
            "detail": payload[:6] if payload else "vazio",
        })

        # ── 3. Campo obrigatório 59 (Nome do beneficiário) ────────────
        nome    = meta.get("nome", "")
        nome_ok = bool(nome and len(nome) >= 2)
        score  -= 0 if nome_ok else 10
        if not nome_ok:
            flags.append("Nome do beneficiário ausente ou muito curto")
        checks.append({
            "label":  "Nome do beneficiário (campo 59)",
            "ok":     nome_ok,
            "detail": nome[:40] if nome else "—",
        })

        # ── 4. Nome suspeito ──────────────────────────────────────────
        nome_lower = nome.lower()
        nome_susp  = any(s in nome_lower for s in SUSPICIOUS_NAMES)
        score     -= 20 if nome_susp else 0
        if nome_susp:
            flags.append(f"Nome do beneficiário suspeito: '{nome}'")
        checks.append({
            "label":  "Nome não está em lista de suspeitos",
            "ok":     not nome_susp,
            "detail": "Nome corresponde a padrões fraudulentos" if nome_susp else "OK",
        })

        # ── 5. Chave Pix válida ────────────────────────────────────────
        chave      = meta.get("chave", "")
        tipo_chave = meta.get("tipo_chave", "")
        chave_ok   = bool(chave and tipo_chave not in ["Desconhecido", ""])
        score     -= 0 if chave_ok else 15
        if not chave_ok:
            flags.append("Chave Pix ausente ou tipo não reconhecido")
        checks.append({
            "label":  "Chave Pix presente e identificada",
            "ok":     chave_ok,
            "detail": f"{tipo_chave}: {chave[:40]}" if chave else "—",
        })

        # ── 6. CPF/CNPJ formato ───────────────────────────────────────
        if tipo_chave == "CPF":
            cpf_ok = self._validate_cpf(chave)
            score -= 0 if cpf_ok else 20
            if not cpf_ok:
                flags.append(f"CPF '{chave}' inválido (dígito verificador incorreto)")
            checks.append({
                "label":  "CPF com dígito verificador válido",
                "ok":     cpf_ok,
                "detail": chave,
            })
        elif tipo_chave == "CNPJ":
            cnpj_ok = self._validate_cnpj(chave)
            score  -= 0 if cnpj_ok else 20
            if not cnpj_ok:
                flags.append(f"CNPJ '{chave}' inválido (dígito verificador incorreto)")
            checks.append({
                "label":  "CNPJ com dígito verificador válido",
                "ok":     cnpj_ok,
                "detail": chave,
            })

        # ── 7. Valor suspeito (>0 e razoável) ─────────────────────────
        valor_str = meta.get("valor", "")
        if valor_str:
            try:
                valor_num = float(valor_str.replace("R$", "").replace(",", ".").strip())
                valor_ok  = 0 < valor_num <= 999999.99
                if not valor_ok:
                    flags.append(f"Valor suspeito: {valor_str}")
                    score -= 10
                checks.append({
                    "label":  "Valor da transação dentro do limite aceitável",
                    "ok":     valor_ok,
                    "detail": valor_str,
                })
            except ValueError:
                flags.append(f"Valor não parseável: {valor_str}")
                checks.append({"label": "Valor parseável", "ok": False, "detail": valor_str})

        # ── 8. URL do payload dinâmico ────────────────────────────────
        url = meta.get("url", "")
        if url:
            url_oficial = any(d in url for d in OFFICIAL_PIX_DOMAINS)
            url_susp    = any(re.search(p, url) for p in SUSPICIOUS_URLS)
            if url_susp:
                flags.append(f"URL do payload com domínio suspeito: {url}")
                score -= 20
            if not url_oficial and not url_susp:
                flags.append(f"URL do payload em domínio não verificado: {url}")
                score -= 5
            checks.append({
                "label":  "URL do payload em domínio oficial Pix",
                "ok":     url_oficial and not url_susp,
                "detail": url[:60],
            })
        else:
            checks.append({
                "label":  "Payload estático (sem URL externa)",
                "ok":     True,
                "detail": "Pix estático — risco de URL ausente",
            })

        # ── 9. Código de país BR ──────────────────────────────────────
        pais    = meta.get("pais", "")
        pais_ok = pais.upper() == "BR" if pais else True  # ausente = não penaliza
        if pais and not pais_ok:
            flags.append(f"País inválido no payload: '{pais}' (esperado 'BR')")
            score -= 10
        if pais:
            checks.append({
                "label":  "Código de país = BR",
                "ok":     pais_ok,
                "detail": pais,
            })

        # ── 10. Moeda BRL ─────────────────────────────────────────────
        moeda    = meta.get("moeda", "")
        moeda_ok = moeda == "BRL" if moeda else True
        if moeda and not moeda_ok:
            flags.append(f"Moeda inválida: '{moeda}' (esperado 'BRL')")
            score -= 10
        if moeda:
            checks.append({
                "label":  "Moeda = BRL (986)",
                "ok":     moeda_ok,
                "detail": moeda,
            })

        # ── 11. GUI Pix correto ───────────────────────────────────────
        gui    = meta.get("gui", "")
        gui_ok = gui.lower() == "br.gov.bcb.pix"
        if gui and not gui_ok:
            flags.append(f"GUI (identificador Pix) inválido: '{gui}'")
            score -= 15
        checks.append({
            "label":  "GUI = br.gov.bcb.pix",
            "ok":     gui_ok,
            "detail": gui or "—",
        })

        # ── 12. Comprimento mínimo do payload ─────────────────────────
        len_ok = len(payload) >= 30
        if not len_ok:
            flags.append("Payload muito curto — possível truncamento ou payload falso")
            score -= 15
        checks.append({
            "label":  "Comprimento mínimo do payload (≥30 chars)",
            "ok":     len_ok,
            "detail": f"{len(payload)} caracteres",
        })

        score = max(0, min(100, score))
        nivel = "BAIXO"   if score >= 80 else ("MÉDIO" if score >= 50 else "ALTO")

        return {
            "score":   score,
            "nivel":   nivel,
            "flags":   flags,
            "checks":  checks,
            "details": {
                "crc_valid":   crc_ok,
                "nome":        nome,
                "chave":       chave,
                "tipo_chave":  tipo_chave,
                "url":         url,
                "formato":     fmt,
            }
        }

    # ── Validadores ───────────────────────────────────────────────────

    def _validate_cpf(self, cpf: str) -> bool:
        cpf = re.sub(r"\D", "", cpf)
        if len(cpf) != 11 or cpf == cpf[0] * 11:
            return False
        for i in range(9, 11):
            s = sum(int(cpf[j]) * (i + 1 - j) for j in range(i))
            d = (s * 10 % 11) % 10
            if d != int(cpf[i]):
                return False
        return True

    def _validate_cnpj(self, cnpj: str) -> bool:
        cnpj = re.sub(r"\D", "", cnpj)
        if len(cnpj) != 14 or cnpj == cnpj[0] * 14:
            return False
        weights1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        weights2 = [6] + weights1
        for weights, pos in [(weights1, 12), (weights2, 13)]:
            s = sum(int(cnpj[i]) * w for i, w in enumerate(weights))
            r = s % 11
            d = 0 if r < 2 else 11 - r
            if d != int(cnpj[pos]):
                return False
        return True
