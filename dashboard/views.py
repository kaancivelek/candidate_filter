from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from jobs.models import Job
from cvs.models import CV
from matching.models import MatchResult

@login_required
def dashboard(request):
    # 1. حساب الإحصائيات العلوية
    active_jobs_count = Job.objects.filter(status='active').count()
    total_cvs_parsed = CV.objects.filter(status='completed').count()
    pending_reviews = CV.objects.filter(status='pending').count()
    
    # نعتبر أن المرشح "مقبول مبدئياً" (Shortlisted) إذا كانت نسبة التطابق 80% أو أعلى
    shortlisted_count = MatchResult.objects.filter(overall_score__gte=80.0).count()

    # 2. جلب أحدث الوظائف مع عدد السير الذاتية المرتبطة بكل وظيفة
    # نستخدم annotate لإضافة حقل وهمي (cv_count) يحتوي على عدد السير الذاتية
    recent_jobs = Job.objects.annotate(
        cv_count=Count('received_cvs')
    ).order_by('-created_at')[:5] # نجلب أحدث 5 وظائف فقط

    # 3. جلب أحدث نشاطات الذكاء الاصطناعي (أحدث تقييمات تمت)
    recent_activities = MatchResult.objects.select_related('cv__candidate', 'job').order_by('-evaluated_at')[:4]

    context = {
        'active_jobs_count': active_jobs_count,
        'total_cvs_parsed': total_cvs_parsed,
        'shortlisted_count': shortlisted_count,
        'pending_reviews': pending_reviews,
        'recent_jobs': recent_jobs,
        'recent_activities': recent_activities,
    }
    
    return render(request, 'dashboard/dashboard.html', context)