import os
import django
import sys
from decimal import Decimal
from datetime import date

# Initialisation de Django
sys.path.append(r"d:\projets\projets pour entreprise\Alliance One\AlliancePlatform")
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'alliance_platform.settings')
django.setup()

from platform_services.identity.models import Organization
from platform_services.education.classes.models import AcademicYear, SchoolClass
from platform_services.education.teachers.models import Teacher
from platform_services.education.subjects.models import Subject
from platform_services.education.students.models import Student
from platform_services.education.grades.models import Grade
from platform_services.education.finance.models import TuitionProfile, Payment

def seed_data():
    org = Organization.objects.first()
    if not org:
        org = Organization.objects.create(name="Alliance One Default", legal_name="Alliance One Default Inc.")
        print(f"Created Org: {org}")

    # Année Scolaire
    ay, _ = AcademicYear.objects.get_or_create(
        organization=org,
        label="2026-2027",
        defaults={"start_year": 2026, "end_year": 2027, "is_active": True}
    )
    print(f"Academic Year: {ay.label}")

    # Classe de Terminale D
    term_d, _ = SchoolClass.objects.get_or_create(
        organization=org,
        name="Terminale D",
        defaults={"level": "Terminale", "section": "Francophone", "academic_year": ay}
    )
    print(f"Class: {term_d}")

    # Professeurs
    prof_math, _ = Teacher.objects.get_or_create(organization=org, first_name="Jean", last_name="Dupont", defaults={"specialty": "Mathématiques", "sex": "M"})
    prof_svt, _ = Teacher.objects.get_or_create(organization=org, first_name="Marie", last_name="Curie", defaults={"specialty": "SVT", "sex": "F"})
    print(f"Teachers: {prof_math}, {prof_svt}")

    # Matières
    math, _ = Subject.objects.get_or_create(organization=org, name="Mathématiques", defaults={"code": "MATH", "coefficient": 4, "level": "Terminale"})
    svt, _ = Subject.objects.get_or_create(organization=org, name="SVT", defaults={"code": "SVT", "coefficient": 4, "level": "Terminale"})
    print(f"Subjects: {math}, {svt}")

    # Elèves
    alice, _ = Student.objects.get_or_create(organization=org, first_name="Alice", last_name="Martin", defaults={"sex": "F", "school_class": term_d, "date_of_birth": date(2008, 1, 1)})
    bob, _ = Student.objects.get_or_create(organization=org, first_name="Bob", last_name="Bernard", defaults={"sex": "M", "school_class": term_d, "date_of_birth": date(2008, 5, 5)})
    print(f"Students: {alice.first_name}, {bob.first_name}")

    # Notes
    Grade.objects.get_or_create(organization=org, student=alice, subject=math, teacher=prof_math, sequence="trim_1", evaluation_type="examen", academic_year=ay, defaults={"value": Decimal("15.5")})
    Grade.objects.get_or_create(organization=org, student=alice, subject=svt, teacher=prof_svt, sequence="trim_1", evaluation_type="examen", academic_year=ay, defaults={"value": Decimal("14.0")})
    Grade.objects.get_or_create(organization=org, student=bob, subject=math, teacher=prof_math, sequence="trim_1", evaluation_type="examen", academic_year=ay, defaults={"value": Decimal("12.0")})
    Grade.objects.get_or_create(organization=org, student=bob, subject=svt, teacher=prof_svt, sequence="trim_1", evaluation_type="examen", academic_year=ay, defaults={"value": Decimal("16.0")})
    print("Grades created.")

    # Finance pour Alice (pension 104000, a payé 98000)
    tp, _ = TuitionProfile.objects.get_or_create(organization=org, student=alice, academic_year=ay, defaults={"total_amount": Decimal("104000")})
    Payment.objects.get_or_create(organization=org, tuition_profile=tp, receipt_number="REC-001", defaults={"amount": Decimal("98000"), "date": date(2026, 9, 15)})
    print(f"Tuition for {alice}: Total={tp.total_amount}, Paid=98000")

    # Génération du bulletin (calcul simple en console pour vérification)
    print("\n" + "="*40)
    print(f"BULLETIN DE NOTES - {ay.label}")
    print(f"Elève: {alice.first_name} {alice.last_name} | Classe: {alice.school_class.name}")
    print("="*40)
    grades = Grade.objects.filter(student=alice, academic_year=ay)
    total_pts = 0
    total_coef = 0
    for g in grades:
        pts = float(g.value) * g.subject.coefficient
        total_pts += pts
        total_coef += g.subject.coefficient
        print(f"{g.subject.name} (Coef {g.subject.coefficient}) : {g.value}/20 -> {pts} pts")
    moyenne = total_pts / total_coef if total_coef else 0
    print("-" * 40)
    print(f"Moyenne Générale : {moyenne:.2f}/20")
    print("="*40)
    
    # Situation Financière
    payments = sum([p.amount for p in tp.payments.all()])
    print(f"Situation Financière: Pension: {tp.total_amount} FCFA | Payé: {payments} FCFA | Reste: {tp.total_amount - payments} FCFA")

if __name__ == "__main__":
    seed_data()
