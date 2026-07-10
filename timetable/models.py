from django.db import models
from django.contrib.auth.models import User


class Department(models.Model):
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name


class Teacher(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    edupage_id = models.CharField(max_length=50, unique=True)
    full_name = models.CharField(max_length=200)
    short_name = models.CharField(max_length=50, blank=True)
    is_dean = models.BooleanField(default=False)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='teachers')
    final_exam_count = models.PositiveIntegerField(default=0)
    midterm_exam_count = models.PositiveIntegerField(default=0)
    retake_exam_count = models.PositiveIntegerField(default=0)

    final_exam_unit = models.CharField(max_length=10, choices=[("groups", "groups"), ("students", "students")],
                                       default="students")
    midterm_exam_unit = models.CharField(max_length=10, choices=[("groups", "groups"), ("students", "students")],
                                         default="students")
    retake_exam_unit = models.CharField(max_length=10, choices=[("groups", "groups"), ("students", "students")],
                                        default="students")
    def __str__(self):
        return self.full_name


class Subject(models.Model):
    edupage_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name


class Classroom(models.Model):
    edupage_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Group(models.Model):
    edupage_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name


class TimetableCard(models.Model):
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name="cards")
    subject = models.ForeignKey(Subject, on_delete=models.SET_NULL, null=True)
    classroom = models.ForeignKey(Classroom, on_delete=models.SET_NULL, null=True, blank=True)
    groups = models.ManyToManyField(Group, blank=True)
    class_names = models.TextField(blank=True)
    day = models.CharField(max_length=20)
    period = models.CharField(max_length=10)

    def __str__(self):
        return f"{self.teacher} | {self.subject} | {self.day} P{self.period}"


class ScheduledLesson(models.Model):
    LESSON_TYPE_CHOICES = [
        ("lecture", "Lecture"),
        ("seminar", "Seminar"),
        ("lab", "Lab"),
        ("exam", "Exam"),
    ]

    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name="scheduled_lessons")
    subject = models.ForeignKey(Subject, on_delete=models.SET_NULL, null=True)
    classroom = models.ForeignKey(Classroom, on_delete=models.SET_NULL, null=True, blank=True)
    groups = models.ManyToManyField(Group, blank=True)
    class_names = models.TextField(blank=True)
    date = models.DateField()
    period = models.CharField(max_length=10)
    day = models.CharField(max_length=20)
    lesson_type = models.CharField(max_length=20, choices=[
        ("lecture", "lecture"), ("seminar", "seminar"), ("lab", "lab"),
        ("exam", "exam"), ("final_exam", "final_exam"),
        ("midterm_exam", "midterm_exam"), ("retake_exam", "retake_exam"),
    ], default="seminar")
    is_rescheduled_slot = models.BooleanField(default=False)  # True if this is a replacement slot
    rescheduled_from = models.ForeignKey(
        'self', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="replacement_slots"
    )
    is_custom_added = models.BooleanField(default=False)
    class Meta:
        unique_together = ("teacher", "date", "period")

    def __str__(self):
        return f"{self.teacher} | {self.date} | Period {self.period} | {self.subject}"


class LessonRecord(models.Model):
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name="lesson_records")
    scheduled_lesson = models.ForeignKey(ScheduledLesson, on_delete=models.CASCADE, null=True, blank=True)
    date = models.DateField()
    is_covered = models.BooleanField(null=True, default=None)
    is_replaced = models.BooleanField(default=False)
    replacement_date = models.DateField(null=True, blank=True)
    note = models.TextField(blank=True)

    class Meta:
        unique_together = ("scheduled_lesson", "date")

    def __str__(self):
        return f"{self.teacher} | {self.date} | {'✓' if self.is_covered else '✗'}"


class MonthlyReport(models.Model):
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE)
    year = models.IntegerField()
    month = models.IntegerField()
    status = models.CharField(max_length=20, choices=[("draft", "draft"), ("submitted", "submitted")], default="draft")
    submitted_at = models.DateTimeField(null=True, blank=True)

    # Dean approval track
    dean_approval = models.CharField(max_length=20, choices=[
        ("pending", "pending"), ("approved", "approved"), ("rejected", "rejected"),
    ], default="pending")
    dean_reviewed_by = models.ForeignKey(Teacher, null=True, blank=True, on_delete=models.SET_NULL, related_name="reports_dean_reviewed")
    dean_reviewed_at = models.DateTimeField(null=True, blank=True)
    dean_rejection_reason = models.TextField(blank=True)

    # Admin approval track — independent of dean's
    admin_approval = models.CharField(max_length=20, choices=[
        ("waiting_dean", "waiting_dean"), ("pending", "pending"), ("approved", "approved"), ("rejected", "rejected"),
    ], default="waiting_dean")
    admin_reviewed_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="reports_admin_reviewed")
    admin_reviewed_at = models.DateTimeField(null=True, blank=True)
    admin_rejection_reason = models.TextField(blank=True)

class ExamAttendance(models.Model):
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name="exam_attendances")
    year = models.IntegerField()
    month = models.IntegerField()
    final_exam_count = models.PositiveIntegerField(default=0)
    final_exam_unit = models.CharField(max_length=10, choices=[("groups","groups"),("students","students")], default="students")
    midterm_exam_count = models.PositiveIntegerField(default=0)
    midterm_exam_unit = models.CharField(max_length=10, choices=[("groups","groups"),("students","students")], default="students")
    retake_exam_count = models.PositiveIntegerField(default=0)
    retake_exam_unit = models.CharField(max_length=10, choices=[("groups","groups"),("students","students")], default="students")

    class Meta:
        unique_together = ("teacher", "year", "month")


class ReportDeadline(models.Model):
    year = models.IntegerField()
    month = models.IntegerField()
    deadline = models.DateField()
    set_by = models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True)

    class Meta:
        unique_together = ("year", "month")

    def __str__(self):
        return f"{self.year}-{self.month} deadline: {self.deadline}"
class RedDay(models.Model):
    date = models.DateField(unique=True)
    reason = models.CharField(max_length=200)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"{self.date} — {self.reason}"

class DepartmentReport(models.Model):
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="monthly_reports")
    year = models.IntegerField()
    month = models.IntegerField()
    submitted_by = models.ForeignKey(Teacher, null=True, blank=True, on_delete=models.SET_NULL, related_name="department_reports_sent")
    submitted_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=[("draft", "draft"), ("submitted", "submitted")], default="draft")
    approval_status = models.CharField(max_length=20, choices=[("pending", "pending"), ("approved", "approved"), ("rejected", "rejected")], default="pending")
    approved_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="department_reports_reviewed")
    approved_at = models.DateTimeField(null=True, blank=True)
    admin_note = models.TextField(blank=True)

    class Meta:
        unique_together = ("department", "year", "month")
class Period(models.Model):
    number = models.CharField(max_length=10, unique=True)
    start_time = models.CharField(max_length=10)
    end_time = models.CharField(max_length=10)

    class Meta:
        ordering = ['number']

    def __str__(self):
        return f"Period {self.number} ({self.start_time}–{self.end_time})"