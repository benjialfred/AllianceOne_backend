import os
import sys
import django
import random
from decimal import Decimal

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'alliance_platform.settings')
django.setup()

from platform_services.identity.models import Organization
from platform_services.education.classes.models import AcademicYear, SchoolClass, Level, Section
from platform_services.education.teachers.models import Teacher
from platform_services.education.subjects.models import Subject
from platform_services.education.students.models import Student, Enrollment
from platform_services.education.grades.models import Grade, Sequence, EvaluationType

def run():
    org = Organization.objects.first()
    if not org:
        print("No organization found. Cannot seed.")
        return

    # 1. Academic Year
    year, _ = AcademicYear.objects.get_or_create(
        organization=org,
        label='2026-2027',
        defaults={'start_year': 2026, 'end_year': 2027, 'is_active': True}
    )

    # 2. Teacher
    teacher, _ = Teacher.objects.get_or_create(
        organization=org,
        first_name='Jean',
        last_name='Dupont',
        defaults={'sex': 'M', 'specialty': 'Mathématiques', 'email': 'jean.dupont@allianceone.com'}
    )

    # 3. Subjects
    math, _ = Subject.objects.get_or_create(organization=org, name='Mathématiques', level='Terminale', defaults={'coefficient': 5, 'group': 1})
    phys, _ = Subject.objects.get_or_create(organization=org, name='Physique', level='Terminale', defaults={'coefficient': 4, 'group': 1})
    fran, _ = Subject.objects.get_or_create(organization=org, name='Français', level='Terminale', defaults={'coefficient': 2, 'group': 2})

    # Level and Section
    level, _ = Level.objects.get_or_create(organization=org, name='Terminale', defaults={'order': 10})
    section, _ = Section.objects.get_or_create(organization=org, name='Scientifique')

    # 4. Class
    school_class, _ = SchoolClass.objects.get_or_create(
        organization=org,
        name='Terminale C',
        academic_year=year,
        defaults={'level': level, 'section': section, 'head_teacher': teacher, 'capacity': 40}
    )
    school_class.subjects.add(math, phys, fran)

    # 5. Students
    students_data = [
        {'first_name': 'Alice', 'last_name': 'Kenfack', 'sex': 'F', 'date_of_birth': '2010-05-14', 'place_of_birth': 'Douala'},
        {'first_name': 'Marc', 'last_name': 'Tchoupo', 'sex': 'M', 'date_of_birth': '2009-11-20', 'place_of_birth': 'Yaoundé'},
        {'first_name': 'Sophie', 'last_name': 'Nga', 'sex': 'F', 'date_of_birth': '2010-01-08', 'place_of_birth': 'Bafoussam'},
    ]

    students = []
    for s_data in students_data:
        student, _ = Student.objects.get_or_create(
            organization=org,
            first_name=s_data['first_name'],
            last_name=s_data['last_name'],
            defaults={
                'sex': s_data['sex'],
                'date_of_birth': s_data['date_of_birth'],
                'place_of_birth': s_data['place_of_birth'],
                'lifecycle_status': 'INSCRIT',
                'parent_name': 'Parent de ' + s_data['first_name'],
                'parent_phone': '690000000'
            }
        )
        students.append(student)
        
        # Create Enrollment
        Enrollment.objects.get_or_create(
            organization=org,
            student=student,
            academic_year=year,
            defaults={'school_class': school_class, 'decision': 'EN_COURS'}
        )

    # 6. Grades for Seq 1 and Seq 2
    subjects = [math, phys, fran]
    sequences = [Sequence.SEQ1, Sequence.SEQ2]

    # Delete existing grades to avoid duplication errors on re-run
    Grade.objects.filter(academic_year=year, student__in=students).delete()

    for student in students:
        for seq in sequences:
            for subject in subjects:
                # Generate realistic grades between 8 and 19
                val = Decimal(random.uniform(8.0, 19.5)).quantize(Decimal('0.01'))
                Grade.objects.create(
                    organization=org,
                    student=student,
                    subject=subject,
                    teacher=teacher,
                    sequence=seq,
                    evaluation_type=EvaluationType.SEQ,
                    academic_year=year,
                    value=val,
                    comment="Bon travail" if val >= 14 else ("Assez bien" if val >= 12 else "Doit faire plus d'efforts")
                )

    print("Seed completed successfully! Added Terminale C, subjects, teacher, 3 students, and Seq1/Seq2 grades.")

if __name__ == '__main__':
    run()
