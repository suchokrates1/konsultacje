import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from PyPDF2 import PdfReader, PdfWriter


def generate_pdf(zajecia, beneficjenci, output_path):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)

    # Pozycje tekstu (zmierzono ręcznie względem PDF-a)
    c.setFont("Helvetica", 12)
    c.drawString(130, 770, zajecia.data.strftime('%d.%m.%Y'))
    start_time = zajecia.godzina_od.strftime('%H:%M')
    end_time = zajecia.godzina_do.strftime('%H:%M')
    time_range = f"{start_time} - {end_time}"
    c.drawString(250, 770, time_range)
    c.drawString(440, 770, zajecia.specjalista)

    for idx, benef in enumerate(beneficjenci[:3]):
        y = 730 - (idx * 30)
        c.drawString(40, y, f"{idx + 1}.")
        c.drawString(70, y, f"{benef.imie}")
        c.drawString(300, y, f"{benef.wojewodztwo}")

    c.save()

    buffer.seek(0)

    # Nałóż na wzór PDF
    template = PdfReader("static/wzor.pdf")
    output = PdfWriter()
    overlay = PdfReader(buffer)

    template_page = template.pages[0]
    template_page.merge_page(overlay.pages[0])
    output.add_page(template_page)

    with open(output_path, "wb") as f:
        output.write(f)
