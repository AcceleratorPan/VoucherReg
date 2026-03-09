from __future__ import annotations

from io import BytesIO

from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from app.core.exceptions import ValidationException


class PDFService:
    async def generate_pdf(self, ordered_image_bytes: list[bytes]) -> bytes:
        if not ordered_image_bytes:
            raise ValidationException(message="No page images found for PDF generation")

        output = BytesIO()
        pdf = canvas.Canvas(output)

        for image_bytes in ordered_image_bytes:
            image_reader = ImageReader(BytesIO(image_bytes))
            width, height = image_reader.getSize()
            pdf.setPageSize((width, height))
            pdf.drawImage(image_reader, 0, 0, width=width, height=height)
            pdf.showPage()

        pdf.save()
        output.seek(0)
        return output.read()
