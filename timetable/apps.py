from django.apps import AppConfig


class TimetableConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'timetable'

    def ready(self):
        try:
            from . import scheduler
            scheduler.start()
        except Exception as e:
            print(f"Scheduler not started: {e}")