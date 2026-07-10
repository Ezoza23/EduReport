import requests
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from timetable.models import Teacher, Subject, Classroom, Group, TimetableCard, LessonRecord, ScheduledLesson

HEADERS = {
    "Content-Type": "application/json",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://ciu.edupage.org/",
    "User-Agent": "Mozilla/5.0"
}
# HEADERS = {
#     "Content-Type": "application/json",
#     "X-Requested-With": "XMLHttpRequest",
#     "Referer": "https://ciu.edupage.org/timetable/",
#     "User-Agent": "Mozilla/5.0",
#     "Cookie": "egdid=8g9C9MMtx8DWt574Cc8CO6DmmRy6Cdqo6ebd83a58b; PHPSESSID=cf5fbca7842960432a7f399ba6a840b0"
# }

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


def decode_days(days_str):
    if not days_str:
        return []
    return [DAY_NAMES[i] for i, ch in enumerate(days_str) if ch == "1"]


def get_upcoming_dates(day_name, weeks=4):
    today = date.today()
    day_index = DAY_NAMES.index(day_name)
    days_since_monday = today.weekday()
    this_monday = today - timedelta(days=days_since_monday)
    dates = []
    for week in range(weeks):
        week_start = this_monday + timedelta(weeks=week)
        target_date = week_start + timedelta(days=day_index)
        if target_date >= today:
            dates.append(target_date)
    return dates


class Command(BaseCommand):
    help = "Sync timetable data from EduPage"

    def handle(self, *args, **kwargs):
        today = date.today()

        self.stdout.write("Fetching from EduPage...")
        data = fetch_data()

        r = data.get("r", {})
        if r.get("error"):
            self.stdout.write(self.style.WARNING(f"  ⚠️ EduPage returned error: {r.get('error')}"))
            self.stdout.write(self.style.WARNING("  Skipping sync — no changes made"))
            return

        if "dbiAccessorRes" not in r:
            self.stdout.write(self.style.WARNING("  ⚠️ EduPage returned no timetable data"))
            self.stdout.write(self.style.WARNING("  Skipping sync — no changes made"))
            return

        tables = r["dbiAccessorRes"]["tables"]

        db = {}
        for table in tables:
            db[table["id"]] = table_to_dict(table)

        # --- Sync Teachers ---
        self.stdout.write("Syncing teachers...")
        for t in db["teachers"]:
            Teacher.objects.update_or_create(
                edupage_id=t["id"],
                defaults={
                    "full_name": t.get("name", ""),
                    "short_name": t.get("short", ""),
                }
            )
        self.stdout.write(f"  ✅ {len(db['teachers'])} teachers")

        # --- Sync Subjects ---
        self.stdout.write("Syncing subjects...")
        for s in db["subjects"]:
            Subject.objects.update_or_create(
                edupage_id=s["id"],
                defaults={"name": s.get("name", "")}
            )
        self.stdout.write(f"  ✅ {len(db['subjects'])} subjects")

        # --- Sync Classrooms ---
        self.stdout.write("Syncing classrooms...")
        for c in db["classrooms"]:
            Classroom.objects.update_or_create(
                edupage_id=c["id"],
                defaults={"name": c.get("name", "")}
            )
        self.stdout.write(f"  ✅ {len(db['classrooms'])} classrooms")

        # --- Sync Groups ---
        self.stdout.write("Syncing groups...")
        for g in db["groups"]:
            Group.objects.update_or_create(
                edupage_id=g["id"],
                defaults={"name": g.get("name", "")}
            )
        self.stdout.write(f"  ✅ {len(db['groups'])} groups")

        self.stdout.write(f"  ✅ {len(db['groups'])} groups")

        # --- Sync Periods ---
        self.stdout.write("Syncing periods...")
        from timetable.models import Period as PeriodModel
        periods_synced = 0
        for p in db.get("periods", []):
            if p.get("starttime") and p.get("endtime"):
                num = p.get("period") or p.get("short") or p.get("id", "")
                if num:
                    PeriodModel.objects.update_or_create(
                        number=str(num),
                        defaults={
                            "start_time": p.get("starttime"),
                            "end_time": p.get("endtime"),
                        }
                    )
                    periods_synced += 1
        self.stdout.write(f"  ✅ {periods_synced} periods")


        # --- Sync Scheduled Lessons ---
        self.stdout.write("Syncing scheduled lessons...")

        lessons_map = {l["id"]: l for l in db["lessons"]}
        classes_map = {c["id"]: c for c in db["classes"]}

        count_created = 0
        count_updated = 0

        # Track which (teacher, date, period) combos are valid per new EduPage data
        valid_keys = set()

        for card in db["cards"]:
            if not card.get("period") or not card.get("days") or "1" not in card.get("days", ""):
                continue

            lesson = lessons_map.get(card.get("lessonid"), {})
            teacher_ids = lesson.get("teacherids", [])
            if not teacher_ids:
                continue

            teacher = Teacher.objects.filter(edupage_id=teacher_ids[0]).first()
            if not teacher:
                continue

            subject = Subject.objects.filter(
                edupage_id=lesson.get("subjectid", "")
            ).first()

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
            days_str = card.get("days", "")

            for i, ch in enumerate(days_str):
                if ch == "1" and i < len(DAY_NAMES):
                    day_name = DAY_NAMES[i]
                    upcoming_dates = get_upcoming_dates(day_name, weeks=1)

                    for lesson_date in upcoming_dates:
                        # Never overwrite past lessons
                        if lesson_date < today:
                            continue

                        valid_keys.add((teacher.id, lesson_date, period))
                        subject_name = str(subject) if subject else ""
                        classroom_name = str(classroom) if classroom else ""
                        from timetable.views import get_lesson_type
                        lesson_type = get_lesson_type(subject_name, classroom_name)
                        sl, created = ScheduledLesson.objects.get_or_create(
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
                            sl.subject = subject
                            sl.classroom = classroom
                            sl.class_names = class_names
                            sl.lesson_type = lesson_type
                            sl.save()
                            count_updated += 1
                        else:
                            count_created += 1

                        sl.groups.set(groups)

        self.stdout.write(f"  ✅ {count_created} created, {count_updated} updated")

        # Remove future lessons that no longer exist in EduPage
        # but keep ones the teacher already interacted with (ticked/rescheduled)
        # Protect this entire week from deletion
        days_since_monday = today.weekday()
        this_monday = today - timedelta(days=days_since_monday)
        this_sunday = this_monday + timedelta(days=6)

        future_lessons = ScheduledLesson.objects.filter(date__gte=today)
        deleted_count = 0
        for sl in future_lessons:
            if sl.is_rescheduled_slot:
                continue
            # Never delete this week's lessons
            if this_monday <= sl.date <= this_sunday:
                continue
            key = (sl.teacher_id, sl.date, sl.period)
            if key not in valid_keys:
                has_record = LessonRecord.objects.filter(scheduled_lesson=sl).exists()
                if not has_record:
                    sl.delete()
                    deleted_count += 1

        self.stdout.write(f"  🗑️ Removed {deleted_count} stale future lessons no longer in EduPage")
        self.stdout.write(self.style.SUCCESS("All done!"))