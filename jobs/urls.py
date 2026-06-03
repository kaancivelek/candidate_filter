from django.urls import path
from . import views

urlpatterns = [
    path('', views.job_list, name='job_list'),
    path('job_form/', views.job_form, name='job_form'),
    path('<int:job_id>/', views.job_detail, name='job_detail'),
    path('<int:job_id>/export/', views.export_candidates, name='export_candidates'),
    path('<int:job_id>/edit/', views.job_edit, name='job_edit'),
    path('<int:job_id>/cv-status/', views.cv_processing_status, name='cv_processing_status'),
]