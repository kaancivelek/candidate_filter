from django.contrib import admin
from .models import MatchResult

@admin.register(MatchResult)
class MatchResultAdmin(admin.ModelAdmin):
    list_display = ('cv', 'job', 'overall_score', 'evaluated_at')
    list_filter = ('job',)
    search_fields = ('cv__candidate__full_name', 'job__title')
    ordering = ('-overall_score',) # ترتيب تنازلي لإظهار أفضل المرشحين أولاً