#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
modules/pix_reporter.py
Gerador de relatório PDF de CyberSec para análise de links Pix.
Segue padrões de relatório CERT.br / ISO/IEC 27035 adaptado.
Created by psyhusk
"""

import datetime
import hashlib
import platform
import sys
import os
from typing import Any


def _ensure_reportlab():
    try:
        import reportlab
        return True
    except ImportError:
        import subprocess
        flags = ["--break-system-packages"] if os.path.exists("/etc/arch-release") else []
        r = subprocess.run(
            [sys.executable, "-m", "pip", "install", "reportlab"] + flags,
            capture_output=True, text=True
        )
        return r.returncode == 0


class PixReporter:
    """Gera relatório PDF de análise Pix conforme padrões de CyberSec."""

    def generate(self, result: dict, output_path: str) -> None:
        if not _ensure_reportlab():
            raise RuntimeError("reportlab não pôde ser instalado. Instale com: pip install reportlab")

        from reportlab.lib.pagesizes    import A4
        from reportlab.lib.styles       import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units        import cm, mm
        from reportlab.lib              import colors
        from reportlab.lib.enums        import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
        from reportlab.platypus         import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
            HRFlowable, PageBreak, KeepTogether
        )
        from reportlab.platypus.flowables import Flowable

        decoded  = result.get("decoded", {})
        analysis = result.get("analysis", {})
        meta     = decoded.get("metadata", {})
        raw      = result.get("raw", "")

        now     = datetime.datetime.now()
        ts      = now.strftime("%d/%m/%Y %H:%M:%S")
        ts_file = now.strftime("%Y%m%d_%H%M%S")

        score = analysis.get("score", 0)
        nivel = analysis.get("nivel", "DESCONHECIDO")
        flags = analysis.get("flags", [])
        checks= analysis.get("checks", [])

        # Cores
        PURPLE_DARK  = colors.HexColor("#1e0a3c")
        PURPLE_MID   = colors.HexColor("#4c1d95")
        PURPLE_LIGHT = colors.HexColor("#7c3aed")
        PURPLE_SOFT  = colors.HexColor("#ede9fe")
        DANGER_COL   = colors.HexColor("#dc2626")
        WARN_COL     = colors.HexColor("#d97706")
        SUCCESS_COL  = colors.HexColor("#16a34a")
        GRAY_DARK    = colors.HexColor("#1f2937")
        GRAY_MID     = colors.HexColor("#4b5563")
        GRAY_LIGHT   = colors.HexColor("#f3f4f6")
        WHITE        = colors.white
        BLACK        = colors.black

        RISK_COLOR   = SUCCESS_COL if score >= 80 else (WARN_COL if score >= 50 else DANGER_COL)

        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            leftMargin=2*cm, rightMargin=2*cm,
            topMargin=2.2*cm, bottomMargin=2*cm,
            title=f"PixieCat — Relatório de Análise Pix",
            author="PixieCat by psyhusk",
            subject="Análise de Autenticidade de Link Pix",
        )

        styles = getSampleStyleSheet()

        def s(name, **kw):
            return ParagraphStyle(name, parent=styles["Normal"], **kw)

        H1  = s("H1",  fontSize=16, textColor=PURPLE_LIGHT, spaceAfter=6,
                        fontName="Helvetica-Bold", leading=20)
        H2  = s("H2",  fontSize=12, textColor=PURPLE_DARK, spaceAfter=4,
                        fontName="Helvetica-Bold", leading=16)
        H3  = s("H3",  fontSize=10, textColor=GRAY_DARK, spaceAfter=3,
                        fontName="Helvetica-Bold", leading=13)
        NRM = s("NRM", fontSize=9,  textColor=GRAY_DARK, spaceAfter=2,
                        leading=13)
        SML = s("SML", fontSize=7.5, textColor=GRAY_MID, spaceAfter=1,
                        leading=11)
        MNO = s("MNO", fontSize=7.5, textColor=GRAY_DARK, fontName="Courier",
                        leading=11, backColor=GRAY_LIGHT, leftIndent=6, rightIndent=6,
                        spaceAfter=2)
        ALT = s("ALT", fontSize=8.5, textColor=DANGER_COL, fontName="Helvetica-Bold",
                        leading=12)
        JUS = s("JUS", fontSize=9, textColor=GRAY_DARK, leading=13, alignment=TA_JUSTIFY)

        story = []

        # ── CAPA ──────────────────────────────────────────────────────
        story.append(Spacer(1, 0.5*cm))

        # Header colorido com título
        header_data = [[
            Paragraph("<b>PixieCat</b>", s("HH", fontSize=22, textColor=WHITE,
                                            fontName="Helvetica-Bold")),
            Paragraph("Relatório de Análise<br/>de Link Pix", s("HR", fontSize=11,
                       textColor=PURPLE_SOFT, fontName="Helvetica", alignment=TA_RIGHT)),
        ]]
        header_tbl = Table(header_data, colWidths=[9*cm, 8*cm])
        header_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,-1), PURPLE_DARK),
            ("TEXTCOLOR",  (0,0), (-1,-1), WHITE),
            ("PADDING",    (0,0), (-1,-1), 14),
            ("VALIGN",     (0,0), (-1,-1), "MIDDLE"),
            ("ROUNDEDCORNERS", [6,6,6,6]),
        ]))
        story.append(header_tbl)
        story.append(Spacer(1, 0.4*cm))

        # Subheader com metadados do relatório
        meta_rel = [
            ["Classificação:", "OSTENSIVO — Uso Interno / Investigativo"],
            ["Gerado em:",     ts],
            ["Ferramenta:",    "PixieCat v1.0.0 — Created by psyhusk"],
            ["Sistema:",       f"{platform.system()} {platform.machine()} / Python {sys.version.split()[0]}"],
            ["Hash do Payload:", hashlib.sha256(raw.encode()).hexdigest()[:32] + "…"],
        ]
        mt = Table(meta_rel, colWidths=[4*cm, 13*cm])
        mt.setStyle(TableStyle([
            ("FONTSIZE", (0,0), (-1,-1), 8),
            ("TEXTCOLOR", (0,0), (0,-1), PURPLE_MID),
            ("FONTNAME",  (0,0), (0,-1), "Helvetica-Bold"),
            ("TEXTCOLOR", (1,0), (1,-1), GRAY_DARK),
            ("BOTTOMPADDING", (0,0), (-1,-1), 3),
            ("TOPPADDING",    (0,0), (-1,-1), 3),
            ("LINEBEFORE", (0,0), (0,-1), 3, PURPLE_LIGHT),
            ("BACKGROUND", (0,0), (-1,-1), GRAY_LIGHT),
        ]))
        story.append(mt)
        story.append(Spacer(1, 0.5*cm))

        # ── 1. SUMÁRIO EXECUTIVO ──────────────────────────────────────
        story.append(Paragraph("1. Sumário Executivo", H1))
        story.append(HRFlowable(width="100%", thickness=1, color=PURPLE_LIGHT))
        story.append(Spacer(1, 0.2*cm))

        risco_label = "BAIXO ✓" if score >= 80 else ("MÉDIO !" if score >= 50 else "ALTO ✗")
        score_data = [[
            Paragraph(f"<b>Score de Autenticidade</b>", s("SC", fontSize=10, textColor=WHITE,
                                                           fontName="Helvetica-Bold")),
            Paragraph(f"<b>{score}/100</b>", s("SCV", fontSize=24, textColor=WHITE,
                                                fontName="Helvetica-Bold", alignment=TA_CENTER)),
            Paragraph(f"Risco: <b>{risco_label}</b>", s("SCI", fontSize=12, textColor=WHITE,
                                                          fontName="Helvetica-Bold")),
        ]]
        st = Table(score_data, colWidths=[6*cm, 4*cm, 7*cm])
        st.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,-1), RISK_COLOR),
            ("PADDING",    (0,0), (-1,-1), 12),
            ("VALIGN",     (0,0), (-1,-1), "MIDDLE"),
            ("ALIGN",      (1,0), (1,0),   "CENTER"),
        ]))
        story.append(st)
        story.append(Spacer(1, 0.3*cm))

        # Resumo narrativo
        if score >= 80:
            summary = (
                "A análise do payload Pix indicou <b>BAIXO RISCO</b> de fraude. "
                "Os principais indicadores de autenticidade foram validados com sucesso, "
                "incluindo integridade CRC-16, formato EMV correto e identificadores Pix "
                "conformes com as normas do Banco Central do Brasil (BACEN). "
                "Recomenda-se, ainda assim, confirmar a identidade do beneficiário antes da transferência."
            )
        elif score >= 50:
            summary = (
                "A análise do payload Pix indicou <b>RISCO MÉDIO</b>. "
                "Foram detectadas inconsistências que merecem atenção antes de prosseguir "
                "com a transferência. Recomenda-se verificação manual dos dados do beneficiário "
                "e confirmação por canal alternativo (ligação, presencial ou app oficial do banco). "
                f"Total de alertas identificados: <b>{len(flags)}</b>."
            )
        else:
            summary = (
                "A análise do payload Pix indicou <b>ALTO RISCO</b> de fraude ou adulteração. "
                "Múltiplas verificações críticas falharam. <b>NÃO realize a transferência</b> "
                "sem investigação aprofundada. Registre um Boletim de Ocorrência (BO) em caso "
                "de tentativa de golpe e reporte ao BACEN via Canal de Atendimento ao Cidadão "
                "(0800-9792345). "
                f"Alertas críticos identificados: <b>{len(flags)}</b>."
            )
        story.append(Paragraph(summary, JUS))
        story.append(Spacer(1, 0.4*cm))

        # ── 2. DADOS DO PAYLOAD ───────────────────────────────────────
        story.append(Paragraph("2. Dados do Payload Analisado", H1))
        story.append(HRFlowable(width="100%", thickness=1, color=PURPLE_LIGHT))
        story.append(Spacer(1, 0.2*cm))

        story.append(Paragraph("2.1 Payload Bruto (Input)", H2))
        payload_txt = raw[:300] + ("…" if len(raw) > 300 else "")
        story.append(Paragraph(payload_txt, MNO))
        story.append(Spacer(1, 0.2*cm))

        story.append(Paragraph("2.2 Metadados Extraídos", H2))
        meta_rows = [
            ["Campo", "Valor"],
            ["Formato",          decoded.get("format", "—")],
            ["Versão EMV",       decoded.get("version", "—")],
            ["Nome Beneficiário", meta.get("nome", "—")],
            ["Chave Pix",        meta.get("chave", "—")],
            ["Tipo de Chave",    meta.get("tipo_chave", "—")],
            ["Valor",            meta.get("valor", "Não especificado")],
            ["Moeda",            meta.get("moeda", "—")],
            ["Cidade",           meta.get("cidade", "—")],
            ["CEP",              meta.get("cep", "—")],
            ["País",             meta.get("pais", "—")],
            ["MCC",              meta.get("mcc", "—")],
            ["TxID",             meta.get("txid", "—")],
            ["Descrição",        meta.get("descricao", "—")],
            ["URL (Dinâmico)",   meta.get("url", "Ausente")],
            ["GUI Pix",          meta.get("gui", "—")],
            ["Banco (ISPB)",     meta.get("banco", "—")],
        ]
        mt2 = Table(meta_rows, colWidths=[5*cm, 12*cm])
        ts2 = TableStyle([
            ("BACKGROUND",  (0,0), (-1,0),  PURPLE_MID),
            ("TEXTCOLOR",   (0,0), (-1,0),  WHITE),
            ("FONTNAME",    (0,0), (-1,0),  "Helvetica-Bold"),
            ("FONTSIZE",    (0,0), (-1,-1), 8.5),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [WHITE, GRAY_LIGHT]),
            ("GRID",        (0,0), (-1,-1), 0.4, colors.HexColor("#d1d5db")),
            ("PADDING",     (0,0), (-1,-1), 5),
            ("VALIGN",      (0,0), (-1,-1), "MIDDLE"),
            ("TEXTCOLOR",   (0,1), (0,-1),  PURPLE_MID),
            ("FONTNAME",    (0,1), (0,-1),  "Helvetica-Bold"),
        ])
        mt2.setStyle(ts2)
        story.append(mt2)
        story.append(Spacer(1, 0.4*cm))

        # ── 3. ANÁLISE DE INTEGRIDADE ─────────────────────────────────
        story.append(Paragraph("3. Análise de Integridade", H1))
        story.append(HRFlowable(width="100%", thickness=1, color=PURPLE_LIGHT))
        story.append(Spacer(1, 0.2*cm))

        story.append(Paragraph("3.1 Verificação CRC-16/CCITT", H2))
        crc_rows = [
            ["Parâmetro",            "Valor"],
            ["CRC calculado",        decoded.get("crc_calculated", "—")],
            ["CRC no payload",       decoded.get("crc_payload", "—")],
            ["Válido",               "✓ SIM" if decoded.get("crc_valid") else "✗ NÃO"],
        ]
        ct = Table(crc_rows, colWidths=[6*cm, 11*cm])
        ct.setStyle(TableStyle([
            ("BACKGROUND",  (0,0), (-1,0),  PURPLE_MID),
            ("TEXTCOLOR",   (0,0), (-1,0),  WHITE),
            ("FONTNAME",    (0,0), (-1,0),  "Helvetica-Bold"),
            ("FONTSIZE",    (0,0), (-1,-1), 8.5),
            ("ROWBACKGROUNDS", (0,1),(-1,-1), [WHITE, GRAY_LIGHT]),
            ("GRID",        (0,0), (-1,-1), 0.4, colors.HexColor("#d1d5db")),
            ("PADDING",     (0,0), (-1,-1), 5),
            ("TEXTCOLOR",   (1,3), (1,3),
             SUCCESS_COL if decoded.get("crc_valid") else DANGER_COL),
            ("FONTNAME",    (1,3), (1,3),  "Helvetica-Bold"),
        ]))
        story.append(ct)
        story.append(Spacer(1, 0.15*cm))
        story.append(Paragraph(
            "O CRC-16/CCITT verifica a integridade do payload EMV. Um CRC inválido indica "
            "adulteração, truncamento ou geração incorreta do QR Code.",
            SML))
        story.append(Spacer(1, 0.3*cm))

        story.append(Paragraph("3.2 Campos EMV Decodificados", H2))
        field_rows = [["ID", "Campo", "Valor"]]
        for f in decoded.get("fields", []):
            val = f["value"][:60] + ("…" if len(f["value"]) > 60 else "")
            field_rows.append([f["id"], f["name"][:35], val])
            for sub in f.get("sub", []):
                sv = sub["value"][:55] + ("…" if len(sub["value"]) > 55 else "")
                field_rows.append(["", f"  └─ {sub['name'][:30]}", sv])

        ft = Table(field_rows, colWidths=[1.2*cm, 6*cm, 9.8*cm])
        ft.setStyle(TableStyle([
            ("BACKGROUND",  (0,0), (-1,0),   PURPLE_DARK),
            ("TEXTCOLOR",   (0,0), (-1,0),   WHITE),
            ("FONTNAME",    (0,0), (-1,0),   "Helvetica-Bold"),
            ("FONTSIZE",    (0,0), (-1,-1),  7.5),
            ("FONTNAME",    (0,0), (-1,0),   "Helvetica-Bold"),
            ("ROWBACKGROUNDS", (0,1),(-1,-1),[WHITE, GRAY_LIGHT]),
            ("GRID",        (0,0), (-1,-1),  0.3, colors.HexColor("#e5e7eb")),
            ("PADDING",     (0,0), (-1,-1),  4),
            ("TEXTCOLOR",   (0,1), (0,-1),   PURPLE_MID),
            ("FONTNAME",    (0,1), (0,-1),   "Courier"),
        ]))
        story.append(ft)
        story.append(Spacer(1, 0.4*cm))

        # ── 4. CHECKLIST DE AUTENTICIDADE ─────────────────────────────
        story.append(Paragraph("4. Checklist de Autenticidade", H1))
        story.append(HRFlowable(width="100%", thickness=1, color=PURPLE_LIGHT))
        story.append(Spacer(1, 0.2*cm))

        chk_rows = [["Status", "Verificação", "Detalhe"]]
        for chk in checks:
            status = "✓ OK" if chk["ok"] else "✗ FALHA"
            chk_rows.append([status, chk["label"], chk.get("detail", "")[:55]])

        cht = Table(chk_rows, colWidths=[1.8*cm, 8*cm, 7.2*cm])
        chk_style = [
            ("BACKGROUND", (0,0), (-1,0),  PURPLE_MID),
            ("TEXTCOLOR",  (0,0), (-1,0),  WHITE),
            ("FONTNAME",   (0,0), (-1,0),  "Helvetica-Bold"),
            ("FONTSIZE",   (0,0), (-1,-1), 8),
            ("ROWBACKGROUNDS", (0,1),(-1,-1),[WHITE, GRAY_LIGHT]),
            ("GRID",       (0,0), (-1,-1), 0.3, colors.HexColor("#e5e7eb")),
            ("PADDING",    (0,0), (-1,-1), 4),
            ("VALIGN",     (0,0), (-1,-1), "MIDDLE"),
        ]
        for i, chk in enumerate(checks, start=1):
            col = SUCCESS_COL if chk["ok"] else DANGER_COL
            chk_style.append(("TEXTCOLOR", (0,i), (0,i), col))
            chk_style.append(("FONTNAME",  (0,i), (0,i), "Helvetica-Bold"))
        cht.setStyle(TableStyle(chk_style))
        story.append(cht)
        story.append(Spacer(1, 0.4*cm))

        # ── 5. ALERTAS E INDICADORES DE COMPROMETIMENTO ───────────────
        story.append(Paragraph("5. Alertas e Indicadores de Comprometimento (IoC)", H1))
        story.append(HRFlowable(width="100%", thickness=1, color=PURPLE_LIGHT))
        story.append(Spacer(1, 0.2*cm))

        if flags:
            for i, fl in enumerate(flags, 1):
                story.append(Paragraph(f"<b>Alerta {i:02d}:</b>  {fl}", ALT))
                story.append(Spacer(1, 0.1*cm))
        else:
            story.append(Paragraph("✓  Nenhum alerta de comprometimento detectado.", s(
                "OK", fontSize=9, textColor=SUCCESS_COL, fontName="Helvetica-Bold")))
        story.append(Spacer(1, 0.3*cm))

        # ── 6. RECOMENDAÇÕES ──────────────────────────────────────────
        story.append(Paragraph("6. Recomendações", H1))
        story.append(HRFlowable(width="100%", thickness=1, color=PURPLE_LIGHT))
        story.append(Spacer(1, 0.2*cm))

        if score >= 80:
            recs = [
                "Confirme o nome do beneficiário exibido no app do banco antes de confirmar o pagamento.",
                "Nunca realize Pix acima de R$ 1.000 sem verificar o destinatário por canal seguro.",
                "Ative os limites de Pix Noturno no app do seu banco para maior segurança.",
                "Desconfie de qualquer pressão ou urgência para realizar a transferência.",
            ]
        elif score >= 50:
            recs = [
                "NÃO confirme o pagamento sem contato direto com o suposto destinatário por telefone conhecido.",
                "Verifique manualmente a chave Pix no site do Banco Central: https://www.bcb.gov.br",
                "Consulte um gerente bancário em caso de dúvida.",
                "Registre print e evidências do link suspeito.",
                "Considere reportar ao BACEN pelo Canal de Atendimento: 0800-9792345.",
            ]
        else:
            recs = [
                "NÃO REALIZE A TRANSFERÊNCIA — alto risco de fraude detectado.",
                "Registre Boletim de Ocorrência (BO) na delegacia ou online (Delegacia Online do estado).",
                "Reporte ao BACEN: 0800-9792345 ou https://www.bcb.gov.br/acessoinformacao/ouvidoria",
                "Salve evidências: screenshots, links, conversas e este relatório.",
                "Alerte familiares e amigos sobre o golpe.",
                "Em caso de transferência já realizada: contate o banco IMEDIATAMENTE para tentativa de devolução via MED (Mecanismo Especial de Devolução).",
            ]

        for i, rec in enumerate(recs, 1):
            story.append(Paragraph(f"{i}. {rec}", NRM))
            story.append(Spacer(1, 0.05*cm))
        story.append(Spacer(1, 0.4*cm))

        # ── 7. INFORMAÇÕES TÉCNICAS ───────────────────────────────────
        story.append(Paragraph("7. Informações Técnicas", H1))
        story.append(HRFlowable(width="100%", thickness=1, color=PURPLE_LIGHT))
        story.append(Spacer(1, 0.2*cm))

        tech_rows = [
            ["Parâmetro",               "Valor"],
            ["Algoritmo CRC",           "CRC-16/CCITT (polinômio 0x1021)"],
            ["Padrão do payload",       "EMV QR Code — ABNT NBR 16883 / BR Code"],
            ["Norma Pix",               "Resolução BCB 1/2020 e Manual de Padrões para Iniciação do Pix"],
            ["Versão da análise",       "PixieCat v1.0.0"],
            ["Hash SHA-256 do payload", hashlib.sha256(raw.encode()).hexdigest()],
            ["Comprimento do payload",  f"{len(raw)} caracteres"],
            ["Timestamp da análise",    ts],
        ]
        techt = Table(tech_rows, colWidths=[5.5*cm, 11.5*cm])
        techt.setStyle(TableStyle([
            ("BACKGROUND",  (0,0), (-1,0),  PURPLE_DARK),
            ("TEXTCOLOR",   (0,0), (-1,0),  WHITE),
            ("FONTNAME",    (0,0), (-1,0),  "Helvetica-Bold"),
            ("FONTSIZE",    (0,0), (-1,-1), 8),
            ("FONTNAME",    (1,1), (1,-1),  "Courier"),
            ("ROWBACKGROUNDS", (0,1),(-1,-1),[WHITE, GRAY_LIGHT]),
            ("GRID",        (0,0), (-1,-1), 0.3, colors.HexColor("#e5e7eb")),
            ("PADDING",     (0,0), (-1,-1), 4),
            ("TEXTCOLOR",   (0,1), (0,-1),  PURPLE_MID),
            ("FONTNAME",    (0,1), (0,-1),  "Helvetica-Bold"),
        ]))
        story.append(techt)
        story.append(Spacer(1, 0.4*cm))

        # ── 8. DISCLAIMER ─────────────────────────────────────────────
        story.append(PageBreak())
        story.append(Paragraph("8. Aviso Legal (Disclaimer)", H1))
        story.append(HRFlowable(width="100%", thickness=1, color=PURPLE_LIGHT))
        story.append(Spacer(1, 0.2*cm))
        disclaimer = (
            "Este relatório foi gerado automaticamente pela ferramenta <b>PixieCat v1.0.0</b>, "
            "desenvolvida por <b>psyhusk</b>, com finalidade exclusivamente educativa, preventiva "
            "e investigativa, sem qualquer vínculo com instituições financeiras, o Banco Central do "
            "Brasil (BACEN) ou autoridades públicas. "
            "<br/><br/>"
            "A análise baseia-se na decodificação do payload EMV conforme o padrão BR Code (ABNT NBR 16883) "
            "e heurísticas de detecção de fraude. <b>Não constitui garantia absoluta</b> de legitimidade "
            "ou fraude — sempre confirme transações com o destinatário por canal seguro independente. "
            "<br/><br/>"
            "O PixieCat não armazena dados analisados nem os transmite a terceiros. "
            "Este documento é confidencial e destinado ao uso do solicitante. "
            "Em caso de fraude confirmada, procure as autoridades competentes."
        )
        story.append(Paragraph(disclaimer, JUS))
        story.append(Spacer(1, 0.5*cm))

        # Rodapé final
        footer_data = [[
            Paragraph("PixieCat v1.0.0 — Created by psyhusk",
                      s("F1", fontSize=7.5, textColor=WHITE, fontName="Helvetica")),
            Paragraph(f"Gerado em {ts}",
                      s("F2", fontSize=7.5, textColor=PURPLE_SOFT,
                        fontName="Helvetica", alignment=TA_RIGHT)),
        ]]
        fft = Table(footer_data, colWidths=[9*cm, 8*cm])
        fft.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,-1), PURPLE_DARK),
            ("PADDING",    (0,0), (-1,-1), 8),
        ]))
        story.append(fft)

        doc.build(story)
