import datetime
from django.db import transaction
from django.shortcuts import get_object_or_404
from platform_services.education.students.models import Student, Enrollment
from platform_services.education.classes.models import SchoolClass, AcademicYear, Level
from platform_services.education.core.models import AuditTrail

class PromotionEngine:
    @staticmethod
    @transaction.atomic
    def process_promotions(source_academic_year_id, target_academic_year_id, decisions, user=None):
        """
        decisions: list of dicts: 
        [
            { 'student_id': 1, 'decision': 'PROMU', 'target_level_id': 2, 'target_class_id': 3 (optional) },
            { 'student_id': 2, 'decision': 'REDOUBLE', 'target_level_id': 1, 'target_class_id': 4 (optional) }
        ]
        """
        source_year = get_object_or_404(AcademicYear, id=source_academic_year_id)
        target_year = get_object_or_404(AcademicYear, id=target_academic_year_id)

        results = {'success': 0, 'errors': []}

        for item in decisions:
            student_id = item.get('student_id')
            decision = item.get('decision')
            target_class_id = item.get('target_class_id')
            
            try:
                student = Student.objects.get(id=student_id)
                current_enrollment = Enrollment.objects.filter(student=student, academic_year=source_year).first()
                
                if not current_enrollment:
                    results['errors'].append(f"Student {student_id} not enrolled in source year.")
                    continue

                # Update current enrollment decision
                current_enrollment.decision = decision
                current_enrollment.save()

                if decision in ['PROMU', 'REDOUBLE']:
                    if not target_class_id:
                        results['errors'].append(f"Student {student_id} requires a target class for promotion/retention.")
                        continue
                        
                    target_class = SchoolClass.objects.get(id=target_class_id)
                    
                    # Create new enrollment
                    new_enrollment = Enrollment.objects.create(
                        student=student,
                        academic_year=target_year,
                        school_class=target_class,
                        decision='EN_COURS',
                        organization_id=student.organization_id
                    )

                    # Update student lifecycle status
                    student.lifecycle_status = 'INSCRIT' if decision == 'PROMU' else 'REDOUBLANT'
                    student.save()

                    # Create audit trail
                    AuditTrail.objects.create(
                        user=user,
                        action='PROMOTION_DECISION',
                        entity_type='Student',
                        entity_id=str(student.id),
                        old_value={'academic_year': source_year.label, 'class': current_enrollment.school_class.name},
                        new_value={'academic_year': target_year.label, 'class': target_class.name, 'decision': decision},
                        reason=f"Council decision: {decision}"
                    )
                    
                    results['success'] += 1
                elif decision in ['EXCLU', 'DIPLOME', 'ABANDON']:
                    student.lifecycle_status = decision
                    student.save()
                    results['success'] += 1
                    
            except Exception as e:
                results['errors'].append(f"Error processing student {student_id}: {str(e)}")

        return results

def promote_students(source_class_id, target_class_id, student_ids):
    # Backward compatibility stub if needed, or to be removed later
    pass

class CalendarEngine:
    @staticmethod
    def is_attendance_suspended(date, organization_id=None):
        """Check if attendance is suspended on a given date (e.g. holidays, exams)"""
        from platform_services.education.classes.models import AcademicEvent
        qs = AcademicEvent.objects.filter(
            start_date__lte=date,
            end_date__gte=date,
            suspends_attendance=True
        )
        if organization_id:
            qs = qs.filter(organization_id=organization_id)
        return qs.exists()
        
    @staticmethod
    def are_grades_locked(date, organization_id=None):
        """Check if grade entry is locked on a given date"""
        from platform_services.education.classes.models import AcademicEvent
        qs = AcademicEvent.objects.filter(
            start_date__lte=date,
            end_date__gte=date,
            locks_grades=True
        )
        if organization_id:
            qs = qs.filter(organization_id=organization_id)
        return qs.exists()

    @staticmethod
    def generate_yearly_events(academic_year, user=None):
        """Generate standard events for a new academic year"""
        from platform_services.education.classes.models import AcademicEvent
        from datetime import timedelta
        
        # Example generation (this would typically use a template or settings)
        start_date = datetime.date(academic_year.start_year, 9, 1) # Sep 1st
        
        AcademicEvent.objects.create(
            title="Rentrée Scolaire",
            event_type="RENTREE",
            start_date=start_date,
            end_date=start_date + timedelta(days=1),
            academic_year=academic_year,
            organization_id=academic_year.organization_id,
            created_by=user
        )
        
        return True
