import uuid
from datetime import datetime
from fpdf import FPDF


def generate_certificate(transaction_data: dict) -> bytes:
    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.add_page()
    pdf.set_auto_page_break(auto=False)

    # Green border
    pdf.set_draw_color(22, 163, 74)
    pdf.set_line_width(1.5)
    pdf.rect(15, 15, 267, 180)

    # Title
    pdf.set_font("Helvetica", "B", 28)
    pdf.set_text_color(21, 128, 61)
    pdf.set_xy(15, 25)
    pdf.cell(267, 15, "Carbon Offset Certificate", align="C")

    # Subtitle
    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(107, 114, 128)
    pdf.set_xy(15, 42)
    pdf.cell(267, 8, "Issued by TerraFoma dMRV Platform", align="C")

    # Certificate ID
    cert_id = str(uuid.uuid4())[:12].upper()
    pdf.set_font("Courier", "", 9)
    pdf.set_text_color(156, 163, 175)
    pdf.set_xy(15, 52)
    pdf.cell(267, 6, f"Certificate #{cert_id}", align="C")

    # Main quantity
    quantity = transaction_data.get("quantity_tco2e", 0)
    pdf.set_font("Helvetica", "B", 48)
    pdf.set_text_color(22, 163, 74)
    pdf.set_xy(15, 62)
    pdf.cell(267, 25, f"{quantity} tCO2e", align="C")

    # Details
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(30, 30, 30)
    y = 95
    details = [
        f"Buyer: {transaction_data.get('buyer_name', 'N/A')} ({transaction_data.get('buyer_company', 'N/A')})",
        f"Land Steward: {transaction_data.get('seller_name', 'N/A')}",
        f"Location: {transaction_data.get('plot_region', 'N/A')} - {transaction_data.get('plot_name', 'N/A')}",
        f"Vintage: {transaction_data.get('vintage_year', 'N/A')}  |  Integrity Score: {transaction_data.get('integrity_score', 'N/A')}/100",
        f"Transaction Date: {transaction_data.get('transaction_date', datetime.utcnow().strftime('%Y-%m-%d'))}",
        f"Verification: AI-Powered dMRV (Sentinel-2 + Random Forest Model v1)",
    ]
    for detail in details:
        pdf.set_xy(40, y)
        pdf.cell(220, 8, detail)
        y += 10

    # Verified badge
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_fill_color(22, 163, 74)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(105, 160)
    pdf.cell(90, 12, "TerraFoma Verified", align="C", fill=True)

    # Footer
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(156, 163, 175)
    tx_id = transaction_data.get("transaction_id", "N/A")
    generated = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    pdf.set_xy(15, 178)
    pdf.cell(
        267,
        5,
        f"Certificate #{cert_id} | Transaction: {tx_id} | Generated: {generated}",
        align="C",
    )

    return pdf.output()
