from django.contrib import admin
from .models import ParsedData, CandidateSkill

@admin.register(ParsedData)
class ParsedDataAdmin(admin.ModelAdmin):
    list_display = ('cv', 'gpa', 'degree', 'parsed_at')
    search_fields = ('cv__candidate__full_name', 'degree')

@admin.register(CandidateSkill)
class CandidateSkillAdmin(admin.ModelAdmin):
    list_display = ('skill_name', 'candidate')
    search_fields = ('skill_name', 'candidate__full_name')