from .models import Grade, EvaluationType, Sequence
from platform_services.education.students.models import Student, Attendance

def get_sequence_average(student_id, academic_year_id, sequence):
    grades = Grade.objects.filter(
        student_id=student_id, academic_year_id=academic_year_id, sequence=sequence
    ).select_related('subject')
    
    subject_averages = {}
    total_coef = 0
    total_points = 0
    
    for grade in grades:
        sub = grade.subject
        if sub.id not in subject_averages:
            subject_averages[sub.id] = {
                'coef': sub.coefficient,
                'grades': {}
            }
        subject_averages[sub.id]['grades'][grade.evaluation_type] = float(grade.value)
        
    for sub_id, data in subject_averages.items():
        g = data['grades']
        seq = g.get(EvaluationType.SEQ)
        cc = g.get(EvaluationType.CC)
        td = g.get(EvaluationType.TD)
        exam = g.get(EvaluationType.EXAM)
        
        if exam is not None:
            average = exam
        elif seq is not None and cc is not None:
            average = (seq * 0.7) + (cc * 0.3)
        elif seq is not None:
            average = seq
        elif cc is not None:
            average = cc
        elif td is not None:
            average = td
        else:
            average = 0.0
            
        total_points += average * data['coef']
        total_coef += data['coef']
        
    return total_points / total_coef if total_coef > 0 else 0.0

def get_class_stats(class_id, academic_year_id, sequence):
    students = Student.objects.filter(enrollments__school_class_id=class_id, enrollments__academic_year_id=academic_year_id).distinct()
    averages = []
    for s in students:
        avg = get_sequence_average(s.id, academic_year_id, sequence)
        if avg > 0:
            averages.append((s.id, avg))
    averages.sort(key=lambda x: x[1], reverse=True)
    
    class_average = sum(a[1] for a in averages) / len(averages) if averages else 0.0
    class_max = averages[0][1] if averages else 0.0
    class_min = averages[-1][1] if averages else 0.0
    return averages, class_average, class_max, class_min

def calculate_student_bulletin(student_id, academic_year_id, sequence):
    display_sequence = sequence
    query_sequence = sequence
    
    if sequence == 'trim1':
        query_sequence = 'seq2'
        display_sequence = 'Trimestre 1'
    elif sequence == 'trim2':
        query_sequence = 'seq4'
        display_sequence = 'Trimestre 2'
    elif sequence == 'trim3':
        query_sequence = 'seq6'
        display_sequence = 'Trimestre 3'
        
    student = Student.objects.get(pk=student_id)
    enrollment = student.enrollments.filter(academic_year_id=academic_year_id).select_related('school_class', 'school_class__head_teacher').first()
    if not enrollment:
        raise ValueError("L'élève n'est pas inscrit pour cette année académique.")
    
    # School settings
    settings = student.organization
    
    grades = Grade.objects.filter(
        student_id=student_id,
        academic_year_id=academic_year_id,
        sequence=query_sequence
    ).select_related('subject', 'teacher')

    absences_count = Attendance.objects.filter(
        student_id=student_id,
        academic_year_id=academic_year_id,
        sequence=query_sequence,
        is_absent=True
    ).count()

    subject_averages = {}
    
    for grade in grades:
        sub = grade.subject
        if sub.id not in subject_averages:
            subject_averages[sub.id] = {
                'subject_name': sub.name,
                'coefficient': sub.coefficient,
                'level': sub.level,
                'group': sub.group,
                'teacher_name': f"{grade.teacher.last_name} {grade.teacher.first_name}",
                'grades': {},
            }
        subject_averages[sub.id]['grades'][grade.evaluation_type] = float(grade.value)

    # Organise by groups
    groups = {
        1: {'subjects': [], 'total_points': 0, 'total_coef': 0},
        2: {'subjects': [], 'total_points': 0, 'total_coef': 0},
        3: {'subjects': [], 'total_points': 0, 'total_coef': 0},
    }

    total_coef = 0
    total_points = 0
    
    for sub_id, data in subject_averages.items():
        g = data['grades']
        
        seq = g.get(EvaluationType.SEQ)
        cc = g.get(EvaluationType.CC)
        td = g.get(EvaluationType.TD)
        exam = g.get(EvaluationType.EXAM)
        
        if exam is not None:
            average = exam
        elif seq is not None and cc is not None:
            average = (seq * 0.7) + (cc * 0.3)
        elif seq is not None:
            average = seq
        elif cc is not None:
            average = cc
        elif td is not None:
            average = td
        else:
            average = 0.0

        coef = data['coefficient']
        total = average * coef
        
        total_points += total
        total_coef += coef
        
        group_idx = data['group']
        if group_idx not in groups:
            group_idx = 1
            
        groups[group_idx]['total_points'] += total
        groups[group_idx]['total_coef'] += coef
        
        appreciation = "Excellent" if average >= 18 else "Très Bien" if average >= 16 else "Bien" if average >= 14 else "Assez Bien" if average >= 12 else "Passable" if average >= 10 else "Faible" if average >= 8 else "Insuffisant"
        
        groups[group_idx]['subjects'].append({
            'subject_id': sub_id,
            'subject_name': data['subject_name'],
            'coefficient': coef,
            'average': round(average, 2),
            'total': round(total, 2),
            'appreciation': appreciation,
            'teacher_name': data['teacher_name']
        })

    # Calculate group averages
    for g_idx, g_data in groups.items():
        if g_data['total_coef'] > 0:
            avg = g_data['total_points'] / g_data['total_coef']
            g_data['average'] = round(avg, 2)
            g_data['appreciation'] = "Excellent" if avg >= 18 else "Très Bien" if avg >= 16 else "Bien" if avg >= 14 else "Assez Bien" if avg >= 12 else "Passable" if avg >= 10 else "Faible" if avg >= 8 else "Insuffisant"
        else:
            g_data['average'] = 0.0
            g_data['appreciation'] = ""

    general_average = total_points / total_coef if total_coef > 0 else 0.0
    
    # Class stats
    class_averages, class_average, class_max, class_min = get_class_stats(enrollment.school_class_id, academic_year_id, query_sequence)
    rank = 1
    for r, (s_id, avg) in enumerate(class_averages, 1):
        if s_id == student_id:
            rank = r
            break
            
    # Mention
    mention = "Excellent" if general_average >= 18 else "Très Bien" if general_average >= 16 else "Bien" if general_average >= 14 else "Assez Bien" if general_average >= 12 else "Passable" if general_average >= 10 else "Faible" if general_average >= 8 else "Insuffisant"
    
    # Decision
    if general_average >= 16:
        decision = "Félicitations du Conseil de Classe !"
    elif general_average >= 14:
        decision = "Tableau d'honneur. Continuez !"
    elif general_average >= 12:
        decision = "Encouragements. Bon travail !"
    elif general_average >= 10:
        decision = "Travail satisfaisant, continuez !"
    elif general_average >= 8:
        decision = "Travail passable, du courage !"
    else:
        decision = "Travail insuffisant, redoublez d'efforts !"
        
    # Trimestre logic
    seq1_avg, seq2_avg = 0, 0
    moy_trim = 0
    if query_sequence == Sequence.SEQ1:
        seq1_avg = general_average
        seq2_avg = 0
        moy_trim = seq1_avg
    elif query_sequence == Sequence.SEQ2:
        seq1_avg = get_sequence_average(student_id, academic_year_id, Sequence.SEQ1)
        seq2_avg = general_average
        moy_trim = (seq1_avg + seq2_avg) / 2 if seq1_avg > 0 else seq2_avg
    elif query_sequence == Sequence.SEQ3:
        seq1_avg = general_average
        seq2_avg = 0
        moy_trim = seq1_avg
    elif query_sequence == Sequence.SEQ4:
        seq1_avg = get_sequence_average(student_id, academic_year_id, Sequence.SEQ3)
        seq2_avg = general_average
        moy_trim = (seq1_avg + seq2_avg) / 2 if seq1_avg > 0 else seq2_avg
    elif query_sequence == Sequence.SEQ5:
        seq1_avg = general_average
        seq2_avg = 0
        moy_trim = seq1_avg
    elif query_sequence == Sequence.SEQ6:
        seq1_avg = get_sequence_average(student_id, academic_year_id, Sequence.SEQ5)
        seq2_avg = general_average
        moy_trim = (seq1_avg + seq2_avg) / 2 if seq1_avg > 0 else seq2_avg

    # Student info for convenience
    head_teacher = enrollment.school_class.head_teacher
    head_teacher_name = f"{head_teacher.first_name} {head_teacher.last_name}" if head_teacher else "Non assigné"

    return {
        'student_id': student_id,
        'student_full_name': f"{student.first_name} {student.last_name}",
        'student_matricule': student.matricule,
        'student_sex': student.sex,
        'student_date_of_birth': str(student.date_of_birth),
        'student_place_of_birth': student.place_of_birth,
        'student_class_name': enrollment.school_class.name,
        'student_class_section': enrollment.school_class.section,
        'head_teacher_name': head_teacher_name,
        'sequence': display_sequence,
        'academic_year_id': academic_year_id,
        'groups': groups,
        'total_points': round(total_points, 2),
        'total_coef': total_coef,
        'general_average': round(general_average, 2),
        'absences_count': absences_count,
        'rank': rank,
        'rank_label': f"{rank}e / {len(class_averages)}",
        'class_total_students': len(class_averages),
        'class_average': round(class_average, 2),
        'class_max': round(class_max, 2),
        'class_min': round(class_min, 2),
        'mention': mention,
        'decision': decision,
        'seq1_avg': round(seq1_avg, 2),
        'seq2_avg': round(seq2_avg, 2),
        'moy_trim': round(moy_trim, 2),
        # School info
        'school_name': settings.name,
        'school_motto': '',
    }

