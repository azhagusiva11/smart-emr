import os
from fpdf import FPDF
from datetime import datetime

class EMRPDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 14)
        self.cell(0, 10, self._safe("Electronic Medical Record (EMR) Summary"), ln=True, align="C")
        self.ln(5)

    def add_section(self, title, content):
        self.set_font("Arial", "B", 12)
        self.cell(0, 10, self._safe(title), ln=True)
        self.set_font("Arial", "", 11)
        if isinstance(content, list):
            for item in content:
                self.multi_cell(0, 8, self._safe(f"- {item}"))
        else:
            self.multi_cell(0, 8, self._safe(content if content else "N/A"))
        self.ln(3)

    def _safe(self, text):
        # Convert problematic unicode characters to safe equivalents or replace
        if text is None:
            return ""
        if not isinstance(text, str):
            text = str(text)
        return text.encode("latin-1", errors="replace").decode("latin-1")

def generate_emr_pdf(patient_data, visit_id, summary, red_flags, prescription):
    pdf = EMRPDF()
    pdf.add_page()

    pdf.set_font("Arial", "", 11)
    pdf.cell(0, 10, pdf._safe(f"Patient ID: {patient_data.get('patient_id', '')}"), ln=True)
    pdf.cell(0, 10, pdf._safe(f"Name: {patient_data.get('name', '')}"), ln=True)
    pdf.cell(0, 10, pdf._safe(f"Age: {patient_data.get('age', '')}, Sex: {patient_data.get('sex', '')}"), ln=True)
    pdf.cell(0, 10, pdf._safe(f"Visit ID: {visit_id}"), ln=True)
    pdf.cell(0, 10, pdf._safe(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}"), ln=True)
    pdf.ln(5)

    pdf.add_section("Clinical Reasoning Summary", summary)
    pdf.add_section("Rare Disease Alerts", red_flags if red_flags else "None triggered")
    pdf.add_section("Prescription", prescription if prescription else "None provided")

    os.makedirs("downloads", exist_ok=True)
    file_path = os.path.join("downloads", f"emr_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
    pdf.output(file_path)
    return file_path
