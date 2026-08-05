from io import BytesIO
from reportlab.pdfgen import canvas

class PdfDocumentService:
    @staticmethod
    def build_bulletin(student, academic_year, sequence):
        buffer = BytesIO()
        p = canvas.Canvas(buffer)
        p.drawString(100, 800, f"Bulletin for {student.first_name} {student.last_name}")
        p.drawString(100, 780, f"Matricule: {student.matricule}")
        p.drawString(100, 760, f"Academic Year: {academic_year.label}")
        p.drawString(100, 740, f"Sequence: {sequence}")
        p.showPage()
        p.save()
        return buffer.getvalue()

    @staticmethod
    def build_class_bulletins(school_class, academic_year, sequence):
        buffer = BytesIO()
        p = canvas.Canvas(buffer)
        p.drawString(100, 800, f"Bulletins for class {school_class.name}")
        p.drawString(100, 760, f"Academic Year: {academic_year.label}")
        p.drawString(100, 740, f"Sequence: {sequence}")
        p.showPage()
        p.save()
        return buffer.getvalue()

    @staticmethod
    def build_school_card(student, academic_year):
        buffer = BytesIO()
        p = canvas.Canvas(buffer)
        p.drawString(100, 800, f"School Card for {student.first_name} {student.last_name}")
        p.drawString(100, 780, f"Matricule: {student.matricule}")
        p.drawString(100, 760, f"Academic Year: {academic_year.label}")
        p.showPage()
        p.save()
        return buffer.getvalue()

    @staticmethod
    def build_class_school_cards(school_class, academic_year):
        buffer = BytesIO()
        p = canvas.Canvas(buffer)
        p.drawString(100, 800, f"School Cards for class {school_class.name}")
        p.drawString(100, 760, f"Academic Year: {academic_year.label}")
        p.showPage()
        p.save()
        return buffer.getvalue()
