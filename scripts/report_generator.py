# scripts/report_generator.py
# Branded Audit Report Generator — ReportLab
# Returns: bytes — feed directly into st.download_button

import io
import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.lib.colors import HexColor


# ── Brand palette ──────────────────────────────────────────────────────────────
PURPLE      = HexColor("#9333ea")
PURPLE_DARK = HexColor("#6b21a8")
SLATE_900   = HexColor("#0f172a")
SLATE_700   = HexColor("#334155")
SLATE_400   = HexColor("#94a3b8")
SLATE_100   = HexColor("#f1f5f9")
RED_600     = HexColor("#dc2626")
AMBER_500   = HexColor("#f59e0b")
GREEN_600   = HexColor("#16a34a")
WHITE       = colors.white


def _risk_color(score):
    """Map risk 1-10 to a traffic-light colour."""
    try:
        s = int(score)
    except (TypeError, ValueError):
        return SLATE_400
    if s <= 3:
        return GREEN_600
    elif s <= 6:
        return AMBER_500
    return RED_600


def _make_styles():
    base = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "LsTitle",
        parent=base["Normal"],
        fontSize=22,
        leading=26,
        textColor=WHITE,
        fontName="Helvetica-Bold",
        alignment=TA_LEFT,
    )
    subtitle_style = ParagraphStyle(
        "LsSubtitle",
        parent=base["Normal"],
        fontSize=10,
        leading=14,
        textColor=HexColor("#d8b4fe"),
        fontName="Helvetica",
        alignment=TA_LEFT,
    )
    section_style = ParagraphStyle(
        "LsSection",
        parent=base["Normal"],
        fontSize=12,
        leading=16,
        textColor=PURPLE,
        fontName="Helvetica-Bold",
        spaceBefore=14,
        spaceAfter=4,
    )
    body_style = ParagraphStyle(
        "LsBody",
        parent=base["Normal"],
        fontSize=9,
        leading=14,
        textColor=SLATE_700,
        fontName="Helvetica",
    )
    bold_body = ParagraphStyle(
        "LsBoldBody",
        parent=body_style,
        fontName="Helvetica-Bold",
        textColor=SLATE_900,
    )
    caption_style = ParagraphStyle(
        "LsCaption",
        parent=base["Normal"],
        fontSize=7.5,
        leading=10,
        textColor=SLATE_400,
        fontName="Helvetica-Oblique",
        alignment=TA_RIGHT,
    )
    warning_style = ParagraphStyle(
        "LsWarning",
        parent=body_style,
        textColor=RED_600,
        fontName="Helvetica-Bold",
        leftIndent=8,
    )
    return {
        "title": title_style,
        "subtitle": subtitle_style,
        "section": section_style,
        "body": body_style,
        "bold_body": bold_body,
        "caption": caption_style,
        "warning": warning_style,
    }


def generate_audit_pdf(audit_results: dict, file_name: str) -> bytes:
    """
    Generate a branded LeaseSight Audit Report PDF.

    Args:
        audit_results: The dict returned by run_full_audit().
        file_name: Original PDF filename (for display purposes).

    Returns:
        PDF as bytes, suitable for st.download_button.
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=1.5 * cm,
        bottomMargin=2 * cm,
    )

    styles = _make_styles()
    story = []
    W, _ = A4
    usable_w = W - 4 * cm  # left + right margins

    risk_score  = audit_results.get("risk_score", "N/A")
    warnings    = audit_results.get("warnings", [])
    findings    = audit_results.get("findings", [])
    summary     = audit_results.get("summary_paragraph", "No summary available.")
    now_str     = datetime.datetime.now().strftime("%B %d, %Y  %H:%M")

    # ── HEADER BANNER ──────────────────────────────────────────────────────────
    header_data = [[
        Paragraph("<b>LeaseSight</b>  AI Audit Report", styles["title"]),
        Paragraph(f"Generated: {now_str}", styles["caption"]),
    ]]
    header_table = Table(header_data, colWidths=[usable_w * 0.72, usable_w * 0.28])
    header_table.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, -1), PURPLE),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",   (0, 0), (-1, -1), 16),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 16),
        ("LEFTPADDING",  (0, 0), (0, -1),  16),
        ("RIGHTPADDING", (-1, 0), (-1, -1), 12),
        ("ROUNDEDCORNERS", [6]),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 0.3 * cm))

    # Subtitle / file strip
    meta_data = [[
        Paragraph(f"Document: <b>{file_name}</b>", styles["body"]),
        Paragraph(
            f'Risk Score: <font color="#{_risk_color(risk_score).hexval()}">'
            f'<b>{risk_score} / 10</b></font>',
            styles["bold_body"]
        ),
    ]]
    meta_table = Table(meta_data, colWidths=[usable_w * 0.70, usable_w * 0.30])
    meta_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), SLATE_100),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING",   (0, 0), (0, -1),  12),
        ("RIGHTPADDING",  (-1, 0), (-1, -1), 12),
        ("LINEBELOW",     (0, 0), (-1, -1), 0.5, SLATE_400),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 0.4 * cm))

    # ── EXECUTIVE BRIEF ────────────────────────────────────────────────────────
    story.append(Paragraph("Executive Brief", styles["section"]))
    story.append(HRFlowable(width=usable_w, thickness=1, color=PURPLE, spaceAfter=6))
    story.append(Paragraph(summary, styles["body"]))
    story.append(Spacer(1, 0.4 * cm))

    # ── RISK ASSESSMENT ────────────────────────────────────────────────────────
    story.append(Paragraph("Risk Assessment", styles["section"]))
    story.append(HRFlowable(width=usable_w, thickness=1, color=PURPLE, spaceAfter=6))

    rc = _risk_color(risk_score)
    risk_label = (
        "LOW RISK — Document is standard and well-structured." if int(risk_score or 0) <= 3
        else "MEDIUM RISK — Some clauses deviate from market norms." if int(risk_score or 0) <= 6
        else "HIGH RISK — Critical issues detected. Review immediately."
    )
    risk_pill_data = [[
        Paragraph(f"Score: <b>{risk_score} / 10</b>", styles["bold_body"]),
        Paragraph(risk_label, styles["body"]),
    ]]
    risk_pill = Table(risk_pill_data, colWidths=[usable_w * 0.18, usable_w * 0.82])
    risk_pill.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (0, -1), rc),
        ("TEXTCOLOR",     (0, 0), (0, -1), WHITE),
        ("BACKGROUND",    (1, 0), (1, -1), HexColor("#fff7ed") if int(risk_score or 0) > 6 else SLATE_100),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING",   (0, 0), (0, -1),  10),
        ("LEFTPADDING",   (1, 0), (1, -1),  10),
        ("ROUNDEDCORNERS", [4]),
    ]))
    story.append(risk_pill)

    if warnings:
        story.append(Spacer(1, 0.25 * cm))
        story.append(Paragraph("Identified Warnings:", styles["bold_body"]))
        for w in warnings:
            story.append(Paragraph(f"⚠  {w}", styles["warning"]))
    story.append(Spacer(1, 0.5 * cm))

    # ── KEY FINDINGS TABLE ─────────────────────────────────────────────────────
    story.append(Paragraph("Key Findings", styles["section"]))
    story.append(HRFlowable(width=usable_w, thickness=1, color=PURPLE, spaceAfter=6))

    if findings:
        table_data = [
            [
                Paragraph("<b>Field</b>", styles["bold_body"]),
                Paragraph("<b>Extracted Value</b>", styles["bold_body"]),
            ]
        ]
        for f in findings:
            lbl = f.get("label", "—")
            val = f.get("value", "—")
            if str(val).lower() == "not found":
                val = "—"
            table_data.append([
                Paragraph(lbl, styles["body"]),
                Paragraph(str(val), styles["body"]),
            ])

        col_w = [usable_w * 0.35, usable_w * 0.65]
        findings_tbl = Table(table_data, colWidths=col_w, repeatRows=1)
        findings_tbl.setStyle(TableStyle([
            # Header row
            ("BACKGROUND",    (0, 0), (-1, 0),  PURPLE),
            ("TEXTCOLOR",     (0, 0), (-1, 0),  WHITE),
            # Alternating rows
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, SLATE_100]),
            # Grid
            ("LINEBELOW",     (0, 0), (-1, -1), 0.4, SLATE_400),
            ("VALIGN",        (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING",    (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING",   (0, 0), (-1, -1), 8),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
        ]))
        story.append(findings_tbl)
    else:
        story.append(Paragraph("No findings extracted.", styles["body"]))

    story.append(Spacer(1, 0.6 * cm))

    # ── FOOTER ─────────────────────────────────────────────────────────────────
    story.append(HRFlowable(width=usable_w, thickness=0.5, color=SLATE_400))
    story.append(Spacer(1, 0.15 * cm))
    story.append(Paragraph(
        "This report was auto-generated by LeaseSight AI Auditor. "
        "It is intended for informational purposes only and does not constitute legal advice.",
        styles["caption"],
    ))

    doc.build(story)
    return buf.getvalue()
