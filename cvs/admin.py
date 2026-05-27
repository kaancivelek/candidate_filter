from django.contrib import admin
from .models import Candidate, CV

@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'phone', 'created_at')
    search_fields = ('full_name', 'email', 'phone')

@admin.register(CV)
class CVAdmin(admin.ModelAdmin):
    list_display = ('candidate', 'job', 'status', 'uploaded_at')
    list_filter = ('status',)
    search_fields = ('candidate__full_name', 'job__title')