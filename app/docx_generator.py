"""Utilities for rendering session details into a DOCX document."""

import os

from flask import current_app
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.shared import Pt


def generate_docx(zajecia, beneficjenci, output_path):
    """Create a DOCX summary for a session and write it to *output_path*."""

    template_path = os.path.join(current_app.root_path, "static", "wzor.docx")
    if not os.path.exists(template_path):
        current_app.logger.error("Missing DOCX template: %s", template_path)
        raise FileNotFoundError(f"Template file not found: {template_path}")

    doc = Document(template_path)
    start_time = zajecia.godzina_od.strftime("%H:%M")
    end_time = zajecia.godzina_do.strftime("%H:%M")
    names = "\n".join(b.imie for b in beneficjenci[:3])
    wojew = ", ".join({b.wojewodztwo for b in beneficjenci[:3]})
    context = {
        "data": zajecia.data.strftime("%d.%m.%Y"),
        "time_range": f"{start_time} - {end_time}",
        "beneficjenci": names,
        "wojewodztwo": wojew,
        "specjalista": zajecia.specjalista,
    }
    current_app.config["_last_docx_context"] = context

    for paragraph in doc.paragraphs:
        text = paragraph.text.strip()
        if text.startswith("Imię i nazwisko beneficjenta:"):
            paragraph.text = "Imię i nazwisko beneficjenta: " + names
        if text.startswith("Województwo:"):
            paragraph.text = "Województwo: " + wojew

    if doc.tables:
        table = doc.tables[0]
        font_size = Pt(16)
        for idx, _ in enumerate(beneficjenci[:3]):
            row = table.rows[idx + 1]
            values = [context["data"], context["time_range"], context["specjalista"]]
            for cell, value in zip(row.cells[1:4], values):
                cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
                p = cell.paragraphs[0]
                p.clear()
                run = p.add_run(value)
                run.font.size = font_size
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    doc.save(output_path)
