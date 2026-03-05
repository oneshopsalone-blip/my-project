import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import landscape
from reportlab.lib.units import mm

CARD_WIDTH = 85.60 * mm
CARD_HEIGHT = 53.98 * mm
SAFE_ZONE = 3 * mm

class VehicleCardPDFGenerator:
    def __init__(self, vehicle):
        self.vehicle = vehicle
        self.buffer = io.BytesIO()
        
    def generate(self):
        c = canvas.Canvas(self.buffer, pagesize=landscape((CARD_WIDTH, CARD_HEIGHT)))
        
        # White background
        c.setFillColorRGB(1, 1, 1)
        c.rect(0, 0, CARD_WIDTH, CARD_HEIGHT, fill=1, stroke=0)
        
        # Draw content
        center_x = CARD_WIDTH / 2
        center_y = CARD_HEIGHT / 2
        
        # Top line: VEHICLE TYPE + DOUBLE SPACE + REGISTRATION (COM  ABC 200)
        c.setFont("Helvetica-Bold", 20)
        c.setFillColorRGB(0, 0, 0)
        # Format with double space between type and registration
        top_text = f"{self.vehicle.vehicle_type.code}  {self.vehicle.vehicle_reg or self.vehicle.vin}"
        c.drawCentredString(center_x, center_y + 8*mm, top_text)
        
        # Bottom line: CATEGORY + NO SPACE + EXPIRY DATE (AP1-03/2027) - SAME FONT AND BOLD
        c.setFont("Helvetica-Bold", 20)  # Same font and bold as top line
        category_code = self.vehicle.category.code if self.vehicle.category else "N/A"
        bottom_text = f"{category_code}-{self.vehicle.expiry_date_formatted}"  # No space, just hyphen
        c.drawCentredString(center_x, center_y - 4*mm, bottom_text)
        
        c.save()
        self.buffer.seek(0)
        return self.buffer