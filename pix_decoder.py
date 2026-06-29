#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
modules/pix_decoder.py
Decodificador de payloads Pix — formato EMV QR Code (BR Code).
Created by psyhusk
"""

import re
import struct
import urllib.parse
from typing import Any


# ── Mapa de IDs EMV do Pix ────────────────────────────────────────────
EMV_FIELDS = {
    "00": "Payload Format Indicator",
    "01": "Point of Initiation Method",
    "02": "Merchant Account Info (Visa)",
    "03": "Merchant Account Info (Mastercard)",
    "04": "Merchant Account Info (Amex)",
    "26": "Merchant Account Info — Pix (GUI)",
    "27": "Merchant Account Info",
    "52": "Merchant Category Code (MCC)",
    "53": "Transaction Currency",
    "54": "Transaction Amount",
    "58": "Country Code",
    "59": "Merchant Name",
    "60": "Merchant City",
    "61": "Postal Code",
    "62": "Additional Data Field",
    "80": "Unreserved Templates",
    "63": "CRC-16",
}

# Sub-campos do ID 26 (Pix)
PIX_26_FIELDS = {
    "00": "GUI (identificador Pix)",
    "01": "Chave Pix",
    "02": "Descrição / Info adicional",
    "03": "URL (payload dinâmico)",
    "25": "URL API Pix",
}

# Sub-campos do ID 62 (Additional Data)
ADDITIONAL_FIELDS = {
    "05": "TxID (Referência da transação)",
    "07": "Terminal Label",
    "08": "Purpose of Transaction",
}

# Mapa ISPB → Nome do banco
ISPB_BANKS = {
    "00000000": "Banco do Brasil",
    "00360305": "Caixa Econômica Federal",
    "00416968": "BNB",
    "00714671": "BTG Pactual",
    "02332886": "XP Investimentos",
    "03311443": "Banco Neon",
    "03656248": "Nubank",
    "04902979": "Banco Inter",
    "07679404": "Banco Itaú",
    "09089356": "Banco Original",
    "09526594": "C6 Bank",
    "10398952": "Banco Safra",
    "10664513": "Mercado Pago",
    "13140088": "Banco Bradesco",
    "14388334": "Banco Santander",
    "15111975": "PagSeguro",
    "20018183": "Pix Banco Central",
    "22896431": "Banco PAN",
    "23114447": "Ame Digital",
    "30306294": "Banco Modal",
    "33264668": "Banco Votorantim",
    "33923798": "Banco Daycoval",
    "60419645": "Unibanco/Itaú",
    "60701190": "Bradesco S.A.",
    "60746948": "Banco Itaú Unibanco",
    "90400888": "Banco Santander (BR)",
    "92702067": "Banco Sicredi",
}


class PixDecoder:
    """
    Decodifica payloads Pix estáticos e dinâmicos.
    Suporta: string EMV bruta, URL pix.bcb.gov.br, links encurtados.
    """

    def decode(self, raw: str) -> dict[str, Any]:
        raw = raw.strip()
        payload_str = self._extract_payload(raw)

        fields    = self._parse_tlv(payload_str)
        crc_calc  = self._crc16(payload_str[:-4])  # sem os 4 últimos chars (CRC)
        crc_pay   = payload_str[-4:].upper() if len(payload_str) >= 4 else "????"
        crc_valid = (crc_calc == crc_pay)

        metadata  = self._extract_metadata(fields, payload_str)
        version   = self._get_field_value(fields, "00")
        fmt       = "Dinâmico" if self._get_field_value(fields, "01") == "12" else "Estático"

        return {
            "raw":            raw,
            "payload":        payload_str,
            "fields":         fields,
            "metadata":       metadata,
            "crc_calculated": crc_calc,
            "crc_payload":    crc_pay,
            "crc_valid":      crc_valid,
            "format":         fmt,
            "version":        version or "01",
        }

    # ── Extração do payload bruto ──────────────────────────────────────

    def _extract_payload(self, raw: str) -> str:
        # URL dinâmico Pix (pix.bcb.gov.br ou similares)
        if raw.lower().startswith("http") and "pix" in raw.lower():
            # payload pode vir como parâmetro 'payload' na URL
            parsed = urllib.parse.urlparse(raw)
            qs     = urllib.parse.parse_qs(parsed.query)
            if "payload" in qs:
                import base64
                try:
                    return base64.b64decode(qs["payload"][0]).decode("utf-8")
                except Exception:
                    pass
            # Senão devolve a URL como payload (será parseado como campo 26.03)
            return self._url_to_emv(raw)

        # QR Code / payload EMV bruto
        if re.match(r"^00\d{2}", raw):
            return raw

        # Base64 simples
        try:
            import base64
            decoded = base64.b64decode(raw + "==").decode("utf-8")
            if re.match(r"^00\d{2}", decoded):
                return decoded
        except Exception:
            pass

        # Tenta usar diretamente
        return raw

    def _url_to_emv(self, url: str) -> str:
        """Constrói EMV mínimo para URL dinâmica Pix."""
        url_encoded = url[:99]
        url_field   = f"03{len(url_encoded):02d}{url_encoded}"
        gui         = "br.gov.bcb.pix"
        gui_field   = f"00{len(gui):02d}{gui}"
        inner       = gui_field + url_field
        field_26    = f"26{len(inner):02d}{inner}"
        base        = f"000201{field_26}520400005303986580{len(url[:25]):02d}{url[:25]}6304"
        crc         = self._crc16(base)
        return base + crc

    # ── Parser TLV (Tag-Length-Value) ─────────────────────────────────

    def _parse_tlv(self, payload: str) -> list[dict]:
        fields  = []
        pos     = 0
        payload = payload.upper() if payload else ""
        payload_orig = payload  # preserve case for values

        # Work on original case for values
        p = self._raw_payload_orig

        while pos < len(p) - 4:
            if pos + 4 > len(p):
                break
            tag = p[pos:pos+2]
            pos += 2
            if pos + 2 > len(p):
                break
            try:
                length = int(p[pos:pos+2])
            except ValueError:
                break
            pos += 2
            value = p[pos:pos+length]
            pos  += length

            tag_up = tag.upper()
            name   = EMV_FIELDS.get(tag_up, f"Campo {tag_up}")
            entry  = {"id": tag_up, "name": name, "value": value, "sub": []}

            # Parse sub-campos do ID 26 (Pix)
            if tag_up == "26":
                entry["sub"] = self._parse_sub(value, PIX_26_FIELDS)

            # Parse sub-campos do ID 62 (Additional Data)
            elif tag_up == "62":
                entry["sub"] = self._parse_sub(value, ADDITIONAL_FIELDS)

            fields.append(entry)

        return fields

    def _parse_sub(self, data: str, field_map: dict) -> list[dict]:
        subs = []
        pos  = 0
        while pos < len(data):
            if pos + 4 > len(data):
                break
            tag = data[pos:pos+2].upper()
            pos += 2
            try:
                length = int(data[pos:pos+2])
            except ValueError:
                break
            pos  += 2
            value = data[pos:pos+length]
            pos  += length
            subs.append({
                "id":    tag,
                "name":  field_map.get(tag, f"Sub {tag}"),
                "value": value,
            })
        return subs

    # ── Extração de metadados semânticos ──────────────────────────────

    def _extract_metadata(self, fields: list, payload: str) -> dict:
        meta = {}

        for f in fields:
            fid = f["id"]
            val = f["value"]

            if fid == "54":
                meta["valor"] = f"R$ {val}"
            elif fid == "53":
                codes = {"986": "BRL", "840": "USD", "978": "EUR"}
                meta["moeda"] = codes.get(val, val)
            elif fid == "58":
                meta["pais"] = val
            elif fid == "59":
                meta["nome"] = val.title()
            elif fid == "60":
                meta["cidade"] = val.title()
            elif fid == "61":
                meta["cep"] = val
            elif fid == "52":
                meta["mcc"] = val
            elif fid == "26":
                for sub in f.get("sub", []):
                    if sub["id"] == "00":
                        meta["gui"] = sub["value"]
                    elif sub["id"] == "01":
                        chave = sub["value"]
                        meta["chave"]      = chave
                        meta["tipo_chave"] = self._detect_key_type(chave)
                        ispb = self._extract_ispb(chave)
                        if ispb:
                            meta["ispb"]  = ispb
                            meta["banco"] = ISPB_BANKS.get(ispb, f"PSP {ispb}")
                    elif sub["id"] == "02":
                        meta["descricao"] = sub["value"]
                    elif sub["id"] == "03":
                        meta["url"] = sub["value"]
            elif fid == "62":
                for sub in f.get("sub", []):
                    if sub["id"] == "05":
                        meta["txid"] = sub["value"]

        return meta

    def _detect_key_type(self, chave: str) -> str:
        chave = chave.strip()
        if re.match(r"^\+55\d{10,11}$", chave) or re.match(r"^\d{10,11}$", chave):
            return "Telefone"
        if re.match(r"^[\w.+-]+@[\w.-]+\.\w+$", chave):
            return "E-mail"
        if re.match(r"^\d{11}$", chave):
            return "CPF"
        if re.match(r"^\d{14}$", chave):
            return "CNPJ"
        if re.match(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$", chave):
            return "Chave Aleatória (EVP)"
        if chave.startswith("http"):
            return "URL (Pix Dinâmico)"
        return "Desconhecido"

    def _extract_ispb(self, chave: str) -> str | None:
        # ISPBs geralmente não estão na chave — retorna None
        # (em Pix real virá da API do BCB, aqui deixamos para análise)
        return None

    def _get_field_value(self, fields: list, fid: str) -> str:
        for f in fields:
            if f["id"] == fid:
                return f["value"]
        return ""

    # ── CRC-16/CCITT ──────────────────────────────────────────────────

    def _crc16(self, data: str) -> str:
        crc = 0xFFFF
        for ch in data.encode("utf-8"):
            crc ^= ch << 8
            for _ in range(8):
                if crc & 0x8000:
                    crc = (crc << 1) ^ 0x1021
                else:
                    crc <<= 1
                crc &= 0xFFFF
        return format(crc, "04X")

    # Guarda payload original para parse case-sensitive
    @property
    def _raw_payload_orig(self):
        return getattr(self, "_payload_orig_val", "")

    def decode(self, raw: str) -> dict[str, Any]:
        raw = raw.strip()
        payload_str = self._extract_payload(raw)
        self._payload_orig_val = payload_str   # preserva para o parser

        fields    = self._parse_tlv(payload_str)
        crc_calc  = self._crc16(payload_str[:-4]) if len(payload_str) >= 4 else "????"
        crc_pay   = payload_str[-4:].upper() if len(payload_str) >= 4 else "????"
        crc_valid = (crc_calc == crc_pay)

        metadata  = self._extract_metadata(fields, payload_str)
        version   = self._get_field_value(fields, "00")
        fmt_code  = self._get_field_value(fields, "01")
        fmt       = "Dinâmico" if fmt_code == "12" else "Estático"

        return {
            "raw":            raw,
            "payload":        payload_str,
            "fields":         fields,
            "metadata":       metadata,
            "crc_calculated": crc_calc,
            "crc_payload":    crc_pay,
            "crc_valid":      crc_valid,
            "format":         fmt,
            "version":        version or "01",
        }
