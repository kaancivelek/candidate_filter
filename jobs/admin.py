from django.contrib import admin
from .models import Job, JobSkill

class JobSkillInline(admin.TabularInline):
    model = JobSkill
    extra = 3  # سيظهر 3 حقول فارغة لإضافة المهارات مباشرة

@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ('title', 'department', 'status', 'created_at')
    list_filter = ('status', 'department')
    search_fields = ('title', 'description')
    inlines = [JobSkillInline]  # دمج المهارات داخل صفحة الوظيفة

@admin.register(JobSkill)
class JobSkillAdmin(admin.ModelAdmin):
    list_display = ('skill_name', 'job')
    search_fields = ('skill_name', 'job__title')