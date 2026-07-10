from django.contrib import admin
from django.urls import path
from timetable import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.login_view, name='login'),
    path('timetable/', views.timetable_view, name='timetable'),
    path('logout/', views.logout_view, name='logout'),
    path('mark-lesson/', views.mark_lesson, name='mark_lesson'),
    path('submit-report/', views.submit_report, name='submit_report'),
path('cancel-report/', views.cancel_report, name='cancel_report'),
    path('dean/', views.dean_dashboard, name='dean_dashboard'),
    path('dean/export/', views.export_dean_excel, name='export_dean_excel'),
path('download-report/', views.download_report, name='download_report'),
path('download-report/<int:teacher_id>/', views.download_report, name='download_report_teacher'),
path('set-language/', views.set_language, name='set_language'),
path('admin-panel/', views.admin_panel, name='admin_panel'),
path('admin-panel/teacher/<int:teacher_id>/', views.admin_teacher_edit, name='admin_teacher_edit'),
path('admin-panel/departments/', views.admin_departments, name='admin_departments'),
path('admin-panel/red-days/', views.admin_red_days, name='admin_red_days'),
path('update-exam-count/', views.update_exam_count, name='update_exam_count'),
path('add-lesson/', views.add_lesson, name='add_lesson'),
path('delete-lesson/<int:lesson_id>/', views.delete_lesson, name='delete_lesson'),
path('submit-department-report/', views.submit_department_report, name='submit_department_report'),
path('cancel-department-report/', views.cancel_department_report, name='cancel_department_report'),
path('review-department-report/<int:report_id>/', views.review_department_report, name='review_department_report'),
path('review-teacher-report/<int:report_id>/', views.review_teacher_report, name='review_teacher_report'),
path('bulk-review-teacher-reports/<int:dept_id>/', views.bulk_review_teacher_reports, name='bulk_review_teacher_reports'),
path('teacher-report/<int:teacher_id>/', views.view_teacher_report, name='view_teacher_report'),
path('department-report/<int:dept_id>/', views.view_department_report, name='view_department_report'),
path('preview-report/', views.preview_report, name='preview_report'),
path('mark-lessons-bulk/', views.mark_lessons_bulk, name='mark_lessons_bulk'),
]