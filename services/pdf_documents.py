from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm, cm
from reportlab.platypus import Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet


class PdfDocumentService:

    @staticmethod
    def _get_appreciation(avg):
        if avg >= 18: return "Excellent"
        if avg >= 16: return "Très Bien"
        if avg >= 14: return "Bien"
        if avg >= 12: return "Assez Bien"
        if avg >= 10: return "Passable"
        if avg >= 8: return "Faible"
        return "Insuffisant"

    @staticmethod
    def build_bulletin(student, academic_year, sequence):
        from platform_services.education.grades.services import calculate_student_bulletin

        try:
            data = calculate_student_bulletin(student.id, academic_year.id, sequence)
        except Exception:
            # Fallback to a simple placeholder if calculation fails
            buffer = BytesIO()
            p = canvas.Canvas(buffer, pagesize=A4)
            p.drawString(100, 800, f"Bulletin pour {student.first_name} {student.last_name}")
            p.drawString(100, 780, f"Erreur lors du calcul des notes.")
            p.showPage()
            p.save()
            return buffer.getvalue()

        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4

        PdfDocumentService._draw_bulletin_page(p, data, width, height, academic_year)

        p.save()
        return buffer.getvalue()

    @staticmethod
    def _draw_bulletin_page(p, data, width, height, academic_year):
        """Draw a single bulletin page."""
        margin = 1.5 * cm
        usable_width = width - 2 * margin

        # --- WATERMARK ---
        p.saveState()
        p.setFont("Helvetica-Bold", 100)
        p.setFillColor(colors.Color(0, 0, 0, alpha=0.03))
        p.translate(width / 2, height / 2)
        p.rotate(45)
        p.drawCentredString(0, 0, "ALLIANCE ONE")
        p.restoreState()

        # --- HEADER ---
        y = height - margin
        p.setFont("Helvetica-Bold", 9)
        p.drawCentredString(margin + usable_width * 0.15, y, "RÉPUBLIQUE DU CAMEROUN")
        y -= 12
        p.setFont("Helvetica", 7)
        p.drawCentredString(margin + usable_width * 0.15, y, "Paix - Travail - Patrie")
        y -= 14
        p.setFont("Helvetica-Bold", 7)
        p.drawCentredString(margin + usable_width * 0.15, y, "MINISTÈRE DES ENSEIGNEMENTS SECONDAIRES")

        # School name (right side)
        y_right = height - margin
        p.setFont("Helvetica-Bold", 10)
        school_name = data.get('school_name', 'Alliance One Education')
        p.drawCentredString(margin + usable_width * 0.85, y_right, school_name.upper())
        y_right -= 14
        p.setFont("Helvetica", 7)
        p.drawCentredString(margin + usable_width * 0.85, y_right, f"Année Scolaire: {academic_year.label}")
        y_right -= 12
        p.drawCentredString(margin + usable_width * 0.85, y_right, f"Séquence: {data.get('sequence', '').upper()}")

        # Separator line
        y = height - margin - 55
        p.setStrokeColor(colors.black)
        p.setLineWidth(1.5)
        p.line(margin, y, width - margin, y)

        # --- TITLE ---
        y -= 25
        p.setFont("Helvetica-Bold", 14)
        p.drawCentredString(width / 2, y, "BULLETIN DE NOTES")
        y -= 5
        p.setLineWidth(0.5)
        p.rect(width / 2 - 80, y - 2, 160, 22, stroke=1, fill=0)

        # --- STUDENT INFO BOX ---
        y -= 30
        box_height = 55
        p.setStrokeColor(colors.black)
        p.setLineWidth(0.5)
        p.rect(margin, y - box_height, usable_width, box_height, stroke=1, fill=0)

        info_y = y - 12
        p.setFont("Helvetica-Bold", 8)
        p.drawString(margin + 8, info_y, "Nom de l'élève :")
        p.setFont("Helvetica", 8)
        p.drawString(margin + 90, info_y, data.get('student_full_name', '').upper())

        info_y -= 13
        p.setFont("Helvetica-Bold", 8)
        p.drawString(margin + 8, info_y, "Matricule :")
        p.setFont("Helvetica", 8)
        p.drawString(margin + 90, info_y, data.get('student_matricule', ''))

        info_y -= 13
        p.setFont("Helvetica-Bold", 8)
        p.drawString(margin + 8, info_y, "Né(e) le :")
        p.setFont("Helvetica", 8)
        dob = data.get('student_date_of_birth', '')
        pob = data.get('student_place_of_birth', '')
        p.drawString(margin + 90, info_y, f"{dob}  à  {pob}")

        info_y -= 13
        p.setFont("Helvetica-Bold", 8)
        p.drawString(margin + 8, info_y, "Sexe :")
        p.setFont("Helvetica", 8)
        p.drawString(margin + 90, info_y, data.get('student_sex', ''))

        # Right side of student info
        info_y = y - 12
        right_col = margin + usable_width * 0.55
        p.setFont("Helvetica-Bold", 8)
        p.drawString(right_col, info_y, "Classe :")
        p.setFont("Helvetica", 8)
        p.drawString(right_col + 70, info_y, data.get('student_class_name', ''))

        info_y -= 13
        p.setFont("Helvetica-Bold", 8)
        p.drawString(right_col, info_y, "Effectif :")
        p.setFont("Helvetica", 8)
        p.drawString(right_col + 70, info_y, f"{data.get('class_total_students', '')} élèves")

        info_y -= 13
        p.setFont("Helvetica-Bold", 8)
        p.drawString(right_col, info_y, "Prof. Principal :")
        p.setFont("Helvetica", 8)
        p.drawString(right_col + 70, info_y, data.get('head_teacher_name', 'Non assigné'))

        # --- GRADES TABLE ---
        y = y - box_height - 15

        group_names = {
            1: 'Enseignements Scientifiques',
            2: 'Enseignements Littéraires',
            3: 'Langues & Autres',
        }

        # Build table data
        table_data = [
            ['Matière / Professeur', 'Coef.', 'Note /20', 'Total', 'Appréciation']
        ]

        groups = data.get('groups', {})
        for group_id in [1, 2, 3]:
            group = groups.get(group_id)
            if not group or len(group.get('subjects', [])) == 0:
                continue

            # Group header row
            table_data.append([group_names.get(group_id, f'Groupe {group_id}'), '', '', '', ''])

            for sub in group['subjects']:
                subject_cell = f"{sub['subject_name']}\n{sub.get('teacher_name', '')}"
                table_data.append([
                    subject_cell,
                    str(sub['coefficient']),
                    str(sub['average']),
                    str(sub['total']),
                    sub['appreciation']
                ])

            # Group subtotal
            table_data.append([
                f"Total {group_names.get(group_id, '')}",
                str(group.get('total_coef', '')),
                str(group.get('average', '')),
                str(round(group.get('total_points', 0), 2)),
                group.get('appreciation', '')
            ])

        # Build and draw the table
        col_widths = [usable_width * 0.38, usable_width * 0.1, usable_width * 0.13, usable_width * 0.13, usable_width * 0.26]

        table = Table(table_data, colWidths=col_widths, repeatRows=1)

        # Determine which rows are headers and subtotals for styling
        style_commands = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.9, 0.9, 0.9)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ]

        # Apply group header and subtotal styling
        row_idx = 1
        for group_id in [1, 2, 3]:
            group = groups.get(group_id)
            if not group or len(group.get('subjects', [])) == 0:
                continue
            # Group header row
            style_commands.append(('BACKGROUND', (0, row_idx), (-1, row_idx), colors.Color(0.85, 0.85, 0.85)))
            style_commands.append(('FONTNAME', (0, row_idx), (-1, row_idx), 'Helvetica-Bold'))
            style_commands.append(('SPAN', (0, row_idx), (-1, row_idx)))
            row_idx += 1

            row_idx += len(group.get('subjects', []))

            # Subtotal row
            style_commands.append(('BACKGROUND', (0, row_idx), (-1, row_idx), colors.Color(0.93, 0.93, 0.93)))
            style_commands.append(('FONTNAME', (0, row_idx), (-1, row_idx), 'Helvetica-Bold'))
            row_idx += 1

        table.setStyle(TableStyle(style_commands))

        table_width, table_height = table.wrap(usable_width, height)
        if y - table_height < margin + 120:
            p.showPage()
            y = height - margin
        table.drawOn(p, margin, y - table_height)
        y = y - table_height - 15

        # --- SUMMARY SECTION ---
        if y < margin + 120:
            p.showPage()
            y = height - margin - 15

        summary_box_width = usable_width * 0.48
        box_h = 85

        # Left: Summary
        p.setStrokeColor(colors.black)
        p.setLineWidth(0.5)
        p.rect(margin, y - box_h, summary_box_width, box_h, stroke=1, fill=0)
        sy = y - 14
        p.setFont("Helvetica-Bold", 9)
        p.drawString(margin + 6, sy, "RÉSUMÉ DU TRAVAIL")
        p.setLineWidth(0.3)
        p.line(margin + 6, sy - 3, margin + summary_box_width - 6, sy - 3)
        sy -= 16
        p.setFont("Helvetica", 8)
        p.drawString(margin + 6, sy, f"Total Points : {data.get('total_points', 0)}")
        sy -= 12
        p.drawString(margin + 6, sy, f"Total Coef : {data.get('total_coef', 0)}")
        sy -= 14
        p.setFont("Helvetica-Bold", 11)
        p.drawString(margin + 6, sy, f"MOYENNE : {data.get('general_average', 0)}/20")
        sy -= 14
        p.setFont("Helvetica", 8)
        p.drawString(margin + 6, sy, f"Rang : {data.get('rank_label', '')}")
        sy -= 12
        p.drawString(margin + 6, sy, f"Absences : {data.get('absences_count', 0)} h")

        # Right: Class Stats
        right_x = margin + usable_width - summary_box_width
        p.rect(right_x, y - box_h, summary_box_width, box_h, stroke=1, fill=0)
        sy = y - 14
        p.setFont("Helvetica-Bold", 9)
        p.drawString(right_x + 6, sy, "STATISTIQUES CLASSE")
        p.line(right_x + 6, sy - 3, right_x + summary_box_width - 6, sy - 3)
        sy -= 16
        p.setFont("Helvetica", 8)
        p.drawString(right_x + 6, sy, f"Moy. Classe : {data.get('class_average', 0)}/20")
        sy -= 12
        p.drawString(right_x + 6, sy, f"Moy. Max : {data.get('class_max', 0)}/20")
        sy -= 12
        p.drawString(right_x + 6, sy, f"Moy. Min : {data.get('class_min', 0)}/20")
        sy -= 14
        p.setFont("Helvetica-Bold", 8)
        p.drawString(right_x + 6, sy, f"Mention : {data.get('mention', '')}")

        y = y - box_h - 15

        # --- DECISIONS & SIGNATURES ---
        if y < margin + 80:
            p.showPage()
            y = height - margin - 15

        third_w = usable_width / 3 - 3
        dec_h = 60

        # Prof Principal
        p.rect(margin, y - dec_h, third_w, dec_h, stroke=1, fill=0)
        p.setFont("Helvetica-Bold", 7)
        p.drawString(margin + 4, y - 10, "Avis du Prof. Principal :")

        # Decision
        p.rect(margin + third_w + 4, y - dec_h, third_w, dec_h, stroke=1, fill=0)
        p.setFont("Helvetica-Bold", 7)
        p.drawString(margin + third_w + 8, y - 10, "Décision du Conseil :")
        p.setFont("Helvetica-Oblique", 7)
        decision_text = data.get('decision', '')
        p.drawString(margin + third_w + 8, y - 25, decision_text[:60])

        # Chef
        p.rect(margin + 2 * (third_w + 4), y - dec_h, third_w, dec_h, stroke=1, fill=0)
        p.setFont("Helvetica-Bold", 7)
        chef_x = margin + 2 * (third_w + 4) + third_w / 2
        p.drawCentredString(chef_x, y - 10, "Le Chef d'Établissement")
        p.setFont("Helvetica", 6)
        p.setFillColor(colors.Color(0.4, 0.4, 0.4))
        p.drawCentredString(chef_x, y - dec_h + 8, "[Signature & Cachet]")
        p.setFillColor(colors.black)

        y = y - dec_h - 20

        # --- FOOTER ---
        p.setFont("Helvetica", 6)
        p.setFillColor(colors.Color(0.5, 0.5, 0.5))
        import datetime
        p.drawCentredString(width / 2, margin - 5, f"Bulletin généré électroniquement par Alliance One — {datetime.date.today().strftime('%d/%m/%Y')}")
        p.setFillColor(colors.black)

        p.showPage()

    @staticmethod
    def build_class_bulletins(school_class, academic_year, sequence):
        from platform_services.education.grades.services import calculate_student_bulletin
        from platform_services.education.students.models import Student

        students = Student.objects.filter(
            enrollments__school_class=school_class,
            enrollments__academic_year=academic_year,
            is_archived=False
        ).distinct().order_by('last_name', 'first_name')

        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4

        if not students.exists():
            p.drawString(100, 800, f"Aucun élève inscrit dans {school_class.name}")
            p.showPage()
            p.save()
            return buffer.getvalue()

        for student in students:
            try:
                data = calculate_student_bulletin(student.id, academic_year.id, sequence)
                PdfDocumentService._draw_bulletin_page(p, data, width, height, academic_year)
            except Exception as e:
                p.setFont("Helvetica", 10)
                p.drawString(100, 800, f"Erreur pour {student.first_name} {student.last_name}: {str(e)}")
                p.showPage()

        p.save()
        return buffer.getvalue()

    @staticmethod
    def build_school_card(student, academic_year):
        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        margin = 1.5 * cm

        # Card dimensions (credit card style, centered)
        card_w = 8.5 * cm
        card_h = 5.4 * cm
        card_x = (width - card_w) / 2
        card_y = height / 2

        # Card background
        p.setStrokeColor(colors.black)
        p.setLineWidth(1)
        p.roundRect(card_x, card_y, card_w, card_h, 8, stroke=1, fill=0)

        # Header stripe
        p.setFillColor(colors.Color(0.1, 0.2, 0.5))
        p.rect(card_x, card_y + card_h - 1.2 * cm, card_w, 1.2 * cm, stroke=0, fill=1)
        p.setFillColor(colors.white)
        p.setFont("Helvetica-Bold", 9)
        school_name = getattr(student.organization, 'name', 'Alliance One Education') if hasattr(student, 'organization') else 'Alliance One Education'
        p.drawCentredString(card_x + card_w / 2, card_y + card_h - 0.8 * cm, school_name.upper())
        p.setFont("Helvetica", 6)
        p.drawCentredString(card_x + card_w / 2, card_y + card_h - 1.05 * cm, "CARTE SCOLAIRE")

        # Student info
        p.setFillColor(colors.black)
        info_y = card_y + card_h - 1.8 * cm
        p.setFont("Helvetica-Bold", 7)
        p.drawString(card_x + 0.3 * cm, info_y, "Nom :")
        p.setFont("Helvetica", 7)
        p.drawString(card_x + 1.5 * cm, info_y, f"{student.first_name} {student.last_name}")

        info_y -= 0.4 * cm
        p.setFont("Helvetica-Bold", 7)
        p.drawString(card_x + 0.3 * cm, info_y, "Matricule :")
        p.setFont("Helvetica", 7)
        p.drawString(card_x + 1.8 * cm, info_y, student.matricule)

        info_y -= 0.4 * cm
        p.setFont("Helvetica-Bold", 7)
        p.drawString(card_x + 0.3 * cm, info_y, "Né(e) le :")
        p.setFont("Helvetica", 7)
        p.drawString(card_x + 1.5 * cm, info_y, f"{student.date_of_birth}  à  {student.place_of_birth}")

        info_y -= 0.4 * cm
        p.setFont("Helvetica-Bold", 7)
        p.drawString(card_x + 0.3 * cm, info_y, "Classe :")
        p.setFont("Helvetica", 7)
        enrollment = student.enrollments.filter(academic_year=academic_year).first()
        class_name = enrollment.school_class.name if enrollment else "N/A"
        p.drawString(card_x + 1.5 * cm, info_y, class_name)

        info_y -= 0.4 * cm
        p.setFont("Helvetica-Bold", 7)
        p.drawString(card_x + 0.3 * cm, info_y, "Année :")
        p.setFont("Helvetica", 7)
        p.drawString(card_x + 1.5 * cm, info_y, academic_year.label)

        # Footer
        p.setFont("Helvetica", 5)
        p.setFillColor(colors.Color(0.5, 0.5, 0.5))
        p.drawCentredString(card_x + card_w / 2, card_y + 0.2 * cm, "Carte générée par Alliance One")

        p.showPage()
        p.save()
        return buffer.getvalue()

    @staticmethod
    def build_class_school_cards(school_class, academic_year):
        from platform_services.education.students.models import Student

        students = Student.objects.filter(
            enrollments__school_class=school_class,
            enrollments__academic_year=academic_year,
            is_archived=False
        ).distinct().order_by('last_name', 'first_name')

        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)

        for student in students:
            card_bytes = PdfDocumentService.build_school_card(student, academic_year)
            # For simplicity, we'll just call the individual card draw inline
            # In a production system, we'd draw multiple cards per page
            width, height = A4
            margin = 1.5 * cm
            card_w = 8.5 * cm
            card_h = 5.4 * cm
            card_x = (width - card_w) / 2
            card_y = height / 2

            p.setStrokeColor(colors.black)
            p.setLineWidth(1)
            p.roundRect(card_x, card_y, card_w, card_h, 8, stroke=1, fill=0)

            p.setFillColor(colors.Color(0.1, 0.2, 0.5))
            p.rect(card_x, card_y + card_h - 1.2 * cm, card_w, 1.2 * cm, stroke=0, fill=1)
            p.setFillColor(colors.white)
            p.setFont("Helvetica-Bold", 9)
            school_name = getattr(student.organization, 'name', 'Alliance One') if hasattr(student, 'organization') else 'Alliance One'
            p.drawCentredString(card_x + card_w / 2, card_y + card_h - 0.8 * cm, school_name.upper())
            p.setFont("Helvetica", 6)
            p.drawCentredString(card_x + card_w / 2, card_y + card_h - 1.05 * cm, "CARTE SCOLAIRE")

            p.setFillColor(colors.black)
            info_y = card_y + card_h - 1.8 * cm
            p.setFont("Helvetica-Bold", 7)
            p.drawString(card_x + 0.3 * cm, info_y, "Nom :")
            p.setFont("Helvetica", 7)
            p.drawString(card_x + 1.5 * cm, info_y, f"{student.first_name} {student.last_name}")
            info_y -= 0.4 * cm
            p.setFont("Helvetica-Bold", 7)
            p.drawString(card_x + 0.3 * cm, info_y, "Matricule :")
            p.setFont("Helvetica", 7)
            p.drawString(card_x + 1.8 * cm, info_y, student.matricule)
            info_y -= 0.4 * cm
            enrollment = student.enrollments.filter(academic_year=academic_year).first()
            class_name = enrollment.school_class.name if enrollment else "N/A"
            p.setFont("Helvetica-Bold", 7)
            p.drawString(card_x + 0.3 * cm, info_y, "Classe :")
            p.setFont("Helvetica", 7)
            p.drawString(card_x + 1.5 * cm, info_y, class_name)
            info_y -= 0.4 * cm
            p.setFont("Helvetica-Bold", 7)
            p.drawString(card_x + 0.3 * cm, info_y, "Année :")
            p.setFont("Helvetica", 7)
            p.drawString(card_x + 1.5 * cm, info_y, academic_year.label)

            p.showPage()

        if not students.exists():
            p.drawString(100, 800, f"Aucun élève dans {school_class.name}")
            p.showPage()

        p.save()
        return buffer.getvalue()
