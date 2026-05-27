from django.urls import path
from . import views

urlpatterns = [
    # مسار عرض الصفحة الرئيسي
    path('', views.cv_repository, name='cv_repository'),
    
    # مسار التصدير الجديد
    path('export/', views.export_cv_database, name='export_cv_database'),
]