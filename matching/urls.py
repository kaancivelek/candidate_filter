from django.urls import path
from . import views

urlpatterns = [
    path('report/<int:match_id>/', views.candidate_report, name='candidate_report')
]