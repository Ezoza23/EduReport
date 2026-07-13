import requests
from datetime import date, timedelta
from timetable.models import Teacher, Subject, Classroom, Group, ScheduledLesson, LessonRecord

HEADERS = {
    "Content-Type": "application/json",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://ciu.edupage.org/",
    "User-Agent": "Mozilla/5.0"
}

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

def fetch_data():
    response = requests.post(
        "https://ciu.edupage.org/timetable/server/regulartt.js?__func=regularttGetData",
        json={"__args": [None, "17"], "__gsh": "00000000"},
        headers=HEADERS
    )
    return response.json()

def table_to_dict(table):
    columns = table.get("data_columns", [])
    rows = table.get("data_rows", [])
    if not rows:
        return []
    if isinstance(rows[0], dict):
        return rows
    return [dict(zip(columns, row)) for row in rows]

def get_upcoming_dates(day_name, weeks=2):
    today = date.today()
    day_index = DAY_NAMES.index(day_name)
    days_since_monday = today.weekday()
    this_monday = today - timedelta(days=days_since_monday)
    dates = []
    for week in range(weeks):
        week_start = this_monday + timedelta(weeks=week)
        target_date = week_start + timedelta(days=day_index)
        if target_date >= today:  # ← this should include today
            dates.append(target_date)
    return dates

def sync_teacher_schedule(teacher, db=None):
    """Sync upcoming scheduled lessons for a specific teacher"""
    if db is None:
        data = fetch_data()
        r = data.get("r", {})
        if r.get("error") or "dbiAccessorRes" not in r:
            return 0, 0
        tables = r["dbiAccessorRes"]["tables"]
        db = {}
        for table in tables:
            db[table["id"]] = table_to_dict(table)

    today = date.today()
    lessons_map = {l["id"]: l for l in db["lessons"]}
    classes_map = {c["id"]: c for c in db["classes"]}
    subjects_map = {s["id"]: s for s in db["subjects"]}
    classrooms_map = {c["id"]: c for c in db["classrooms"]}
    groups_map = {g["id"]: g for g in db["groups"]}

    created_count = 0
    updated_count = 0

    # Track which (date, period) combos are valid per latest EduPage data
    valid_keys = set()

    for card in db["cards"]:
        if not card.get("period") or not card.get("days") or "1" not in card.get("days", ""):
            continue

        lesson = lessons_map.get(card.get("lessonid"), {})
        teacher_ids = lesson.get("teacherids", [])
        if not teacher_ids:
            continue

        # Only process cards for this specific teacher
        if teacher_ids[0] != teacher.edupage_id:
            continue

        subject_id = lesson.get("subjectid", "")
        subject = Subject.objects.filter(edupage_id=subject_id).first()

        classroom_ids = card.get("classroomids", [])
        classroom = Classroom.objects.filter(
            edupage_id=classroom_ids[0]
        ).first() if classroom_ids else None

        class_ids = lesson.get("classids", [])
        class_names = ", ".join([
            classes_map.get(cid, {}).get("name", cid)
            for cid in class_ids
        ])

        group_ids = lesson.get("groupids", [])
        groups = Group.objects.filter(edupage_id__in=group_ids)

        period = card.get("period", "")

        # Decode days
        days_str = card.get("days", "")
        for i, ch in enumerate(days_str):
            if ch == "1" and i < len(DAY_NAMES):
                day_name = DAY_NAMES[i]
                upcoming_dates = get_upcoming_dates(day_name, weeks=1)

                for lesson_date in upcoming_dates:
                    # Never overwrite past lessons
                    if lesson_date < today:
                        continue

                    valid_keys.add((lesson_date, period))
                    subject_name = str(subject) if subject else ""
                    classroom_name = str(classroom) if classroom else ""
                    from timetable.views import get_lesson_type
                    lesson_type = get_lesson_type(subject_name, classroom_name)
                    scheduled, created = ScheduledLesson.objects.get_or_create(
                        teacher=teacher,
                        date=lesson_date,
                        period=period,
                        defaults={
                            "subject": subject,
                            "classroom": classroom,
                            "class_names": class_names,
                            "day": day_name,
                            "lesson_type": lesson_type,
                        }
                    )

                    if not created:
                        scheduled.subject = subject
                        scheduled.classroom = classroom
                        scheduled.class_names = class_names
                        scheduled.lesson_type = lesson_type
                        scheduled.save()
                        updated_count += 1
                    else:
                        created_count += 1

                    scheduled.groups.set(groups)

        # Remove this teacher's future lessons no longer present in EduPage,
        # but keep any the teacher already interacted with
        # Protect this entire week from deletion
        days_since_monday = today.weekday()
        this_monday = today - timedelta(days=days_since_monday)
        this_sunday = this_monday + timedelta(days=6)

        future_lessons = ScheduledLesson.objects.filter(teacher=teacher, date__gte=today)
        deleted_count = 0
        for sl in future_lessons:
            # Never delete replacement slots
            if sl.is_rescheduled_slot:
                continue
            # Never delete this week's lessons
            if this_monday <= sl.date <= this_sunday:
                continue
            key = (sl.date, sl.period)
            if key not in valid_keys:
                has_record = LessonRecord.objects.filter(scheduled_lesson=sl).exists()
                if not has_record:
                    sl.delete()
                    deleted_count += 1

    return created_count, updated_count