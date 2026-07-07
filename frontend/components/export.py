"""
Export utilities: CSV, Excel, PDF report generation.
All functions return bytes ready to pass to st.download_button().
"""
import io
import logging
from typing import Any, Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)


def results_to_dataframe(results: List[Dict[str, Any]]) -> pd.DataFrame:
    """Convert ranking results list to a tidy DataFrame."""
    rows = []
    for r in results:
        rows.append(
            {
                "Rank": r.get("rank"),
                "Candidate": r.get("candidate_name", "Unknown"),
                "Score (%)": r.get("similarity_score"),
                "Recommendation": r.get("recommendation"),
                "Matched Skills": ", ".join(r.get("matched_skills", [])),
                "Missing Skills": ", ".join(r.get("missing_skills", [])),
                "Extra Skills": ", ".join(r.get("extra_skills", [])),
                "Experience (years)": r.get("experience_years", 0),
                "Quality Score": r.get("quality_score", 0),
                "Keyword Density (%)": r.get("keyword_density", 0),
                "Filename": r.get("filename", ""),
            }
        )
    return pd.DataFrame(rows)


def to_csv(results: List[Dict[str, Any]]) -> bytes:
    df = results_to_dataframe(results)
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue().encode("utf-8")


def to_excel(results: List[Dict[str, Any]], job_title: str = "") -> bytes:
    df = results_to_dataframe(results)
    buf = io.BytesIO()

    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Rankings")

        # Auto-width columns
        ws = writer.sheets["Rankings"]
        for col in ws.columns:
            max_len = max(len(str(cell.value or "")) for cell in col)
            ws.column_dimensions[col[0].column_letter].width = min(max_len + 4, 60)

        # Summary sheet
        summary_data = {
            "Job Title": [job_title],
            "Total Candidates": [len(results)],
            "Average Score": [round(df["Score (%)"].mean(), 2) if not df.empty else 0],
            "Top Candidate": [df.iloc[0]["Candidate"] if not df.empty else "N/A"],
            "Top Score": [df.iloc[0]["Score (%)"] if not df.empty else 0],
        }
        pd.DataFrame(summary_data).to_excel(writer, index=False, sheet_name="Summary")

    return buf.getvalue()


def to_pdf_report(
    results: List[Dict[str, Any]],
    job_title: str = "",
    job_description: str = "",
) -> bytes:
    """Generate a PDF ranking report using reportlab."""
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )

        buf = io.BytesIO()
        doc = SimpleDocTemplate(
            buf,
            pagesize=A4,
            rightMargin=20 * mm,
            leftMargin=20 * mm,
            topMargin=20 * mm,
            bottomMargin=20 * mm,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "Title",
            parent=styles["Heading1"],
            fontSize=18,
            spaceAfter=6,
            textColor=colors.HexColor("#2c3e50"),
        )
        subtitle_style = ParagraphStyle(
            "Subtitle",
            parent=styles["Normal"],
            fontSize=11,
            spaceAfter=12,
            textColor=colors.HexColor("#7f8c8d"),
        )

        story = []
        story.append(Paragraph("AI-Powered Resume Ranking Report", title_style))
        story.append(Paragraph(f"Job: {job_title}", subtitle_style))
        story.append(Paragraph(f"Total Candidates Evaluated: {len(results)}", styles["Normal"]))
        story.append(Spacer(1, 6 * mm))

        # Table header
        table_data = [[
            "Rank", "Candidate", "Score (%)", "Recommendation",
            "Matched Skills", "Missing Skills",
        ]]

        rec_colours = {
            "Excellent Candidate": colors.HexColor("#d5f5e3"),
            "Strong Match": colors.HexColor("#eafaf1"),
            "Suitable": colors.HexColor("#fef9e7"),
            "Average Match": colors.HexColor("#fdebd0"),
            "Not Recommended": colors.HexColor("#fde8e8"),
        }
        row_colours = []

        for r in results:
            matched = ", ".join(r.get("matched_skills", [])[:5])
            missing = ", ".join(r.get("missing_skills", [])[:5])
            table_data.append([
                str(r.get("rank", "")),
                r.get("candidate_name", "Unknown"),
                f"{r.get('similarity_score', 0):.1f}",
                r.get("recommendation", ""),
                matched or "—",
                missing or "—",
            ])
            row_colours.append(rec_colours.get(r.get("recommendation", ""), colors.white))

        col_widths = [15 * mm, 40 * mm, 22 * mm, 38 * mm, 45 * mm, 45 * mm]
        table = Table(table_data, colWidths=col_widths, repeatRows=1)

        style_cmds = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 10),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f9fa")]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#bdc3c7")),
            ("FONTSIZE", (0, 1), (-1, -1), 9),
            ("PADDING", (0, 0), (-1, -1), 4),
        ]

        # Colour rows by recommendation
        for i, colour in enumerate(row_colours, start=1):
            style_cmds.append(("BACKGROUND", (0, i), (-1, i), colour))

        table.setStyle(TableStyle(style_cmds))
        story.append(table)

        doc.build(story)
        return buf.getvalue()

    except ImportError:
        logger.warning("reportlab not installed — returning empty PDF.")
        return b""
