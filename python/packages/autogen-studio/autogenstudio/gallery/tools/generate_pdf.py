import unicodedata
import uuid
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Optional

import requests
from autogen_core.code_executor import ImportFromModule
from autogen_core.tools import FunctionTool
from fpdf import FPDF
from PIL import Image, ImageDraw, ImageOps


async def generate_pdf(
    sections: List[Dict[str, Optional[str]]], output_file: str = "report.pdf", report_title: str = "PDF Report"
) -> str:
    """
    Generate a PDF report with formatted sections including text and images.

    Args:
        sections: List of dictionaries containing section details with keys:
            - title: Section title
            - level: Heading level (title, h1, h2)
            - content: Section text content
            - image: Optional image URL or file path
        output_file: Name of output PDF file
        report_title: Title shown at top of report

    Returns:
        str: Path to the generated PDF file
    """

    def normalize_text(text: str) -> str:
        """Normalize Unicode text to ASCII."""
        return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")

    def get_image(image_url_or_path):
        """Fetch image from URL or local path."""
        if image_url_or_path.startswith(("http://", "https://")):
            response = requests.get(image_url_or_path)
            if response.status_code == 200:
                return BytesIO(response.content)
        elif Path(image_url_or_path).is_file():
            return open(image_url_or_path, "rb")
        return None

    def add_rounded_corners(img, radius=6):
        """Add rounded corners to an image."""
        mask = Image.new("L", img.size, 0)
        draw = ImageDraw.Draw(mask)
        draw.rounded_rectangle([(0, 0), img.size], radius, fill=255)
        img = ImageOps.fit(img, mask.size, centering=(0.5, 0.5))
        img.putalpha(mask)
        return img

    class PDF(FPDF):
        """Custom PDF class with header and content formatting."""

        def header(self):
            self.set_font("Arial", "B", 12)
            normalized_title = normalize_text(report_title)
            self.cell(0, 10, normalized_title, 0, 1, "C")

        def chapter_title(self, txt):
            self.set_font("Arial", "B", 12)
            normalized_txt = normalize_text(txt)
            self.cell(0, 10, normalized_txt, 0, 1, "L")
            self.ln(2)

        def chapter_body(self, body):
            self.set_font("Arial", "", 12)
            normalized_body = normalize_text(body)
            self.multi_cell(0, 10, normalized_body)
            self.ln()

        def add_image(self, img_data):
            img = Image.open(img_data)
            img = add_rounded_corners(img)
            img_path = Path(f"temp_{uuid.uuid4().hex}.png")
            img.save(img_path, format="PNG")
            self.image(str(img_path), x=None, y=None, w=190 if img.width > 190 else img.width)
            self.ln(10)
            img_path.unlink()

    # Initialize PDF
    pdf = PDF()
    pdf.add_page()
    font_size = {"title": 16, "h1": 14, "h2": 12, "body": 12}

    # Add sections
    for section in sections:
        title = section.get("title", "")
        level = section.get("level", "h1")
        content = section.get("content", "")
        image = section.get("image")

        pdf.set_font("Arial", "B" if level in font_size else "", font_size.get(level, font_size["body"]))
        pdf.chapter_title(title)

        if content:
            pdf.chapter_body(content)

        if image:
            img_data = get_image(image)
            if img_data:
                pdf.add_image(img_data)
                if isinstance(img_data, BytesIO):
                    img_data.close()

    pdf.output(output_file)
    return output_file


# Create the PDF generation tool
generate_pdf_tool = FunctionTool(
    func=generate_pdf,
    description="Generate PDF reports with formatted sections containing text and images",
    global_imports=[
        "uuid",
        "requests",
        "unicodedata",
        ImportFromModule("typing", ("List", "Dict", "Optional")),
        ImportFromModule("pathlib", ("Path",)),
        ImportFromModule("fpdf", ("FPDF",)),
        ImportFromModule("PIL", ("Image", "ImageDraw", "ImageOps")),
        ImportFromModule("io", ("BytesIO",)),
    ],
)
