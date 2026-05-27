import csv
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta
from django.http import HttpResponse

from .models import CV
from jobs.models import Job

@login_required
def cv_repository(request):
    # 1. جلب جميع السير الذاتية
    cv_list = CV.objects.select_related('candidate', 'job', 'match_result').prefetch_related('candidate__skills').order_by('-uploaded_at')

    # 2. تطبيق فلتر البحث النصي (الاسم، الإيميل، أو المهارات)
    search_query = request.GET.get('search', '')
    if search_query:
        cv_list = cv_list.filter(
            Q(candidate__full_name__icontains=search_query) |
            Q(candidate__email__icontains=search_query) |
            Q(candidate__skills__skill_name__icontains=search_query)
        ).distinct() # distinct مهمة جداً لمنع تكرار السير الذاتية بسبب المهارات

    # 3. تطبيق فلتر الوظيفة الأصلية
    job_filter = request.GET.get('job', 'all')
    if job_filter != 'all' and job_filter.isdigit():
        cv_list = cv_list.filter(job_id=job_filter)

    # 4. تطبيق فلتر تاريخ الرفع
    date_filter = request.GET.get('date', 'all')
    now = timezone.now()
    if date_filter == 'today':
        cv_list = cv_list.filter(uploaded_at__date=now.date())
    elif date_filter == 'week':
        cv_list = cv_list.filter(uploaded_at__gte=now - timedelta(days=7))
    elif date_filter == 'month':
        cv_list = cv_list.filter(uploaded_at__gte=now - timedelta(days=30))

    # 5. الترقيم (Pagination)
    paginator = Paginator(cv_list, 10) # 10 سير ذاتية في كل صفحة
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    jobs = Job.objects.all().order_by('-created_at')

    context = {
        'page_obj': page_obj,
        'jobs': jobs,
        'search_query': search_query,
        'job_filter': job_filter,
        'date_filter': date_filter,
    }
    
    return render(request, 'cvs/cv_repository.html', context)


@login_required
def export_cv_database(request):
    """
    هذه الدالة تقوم بتوليد ملف CSV يحتوي على السير الذاتية
    وتأخذ بعين الاعتبار نفس الفلاتر التي اختارها المستخدم.
    """
    cv_list = CV.objects.select_related('candidate', 'job', 'match_result').prefetch_related('candidate__skills').order_by('-uploaded_at')

    # تطبيق نفس الفلاتر (البحث، الوظيفة، التاريخ)
    search_query = request.GET.get('search', '')
    if search_query:
        cv_list = cv_list.filter(
            Q(candidate__full_name__icontains=search_query) |
            Q(candidate__email__icontains=search_query) |
            Q(candidate__skills__skill_name__icontains=search_query)
        ).distinct()

    job_filter = request.GET.get('job', 'all')
    if job_filter != 'all' and job_filter.isdigit():
        cv_list = cv_list.filter(job_id=job_filter)

    date_filter = request.GET.get('date', 'all')
    now = timezone.now()
    if date_filter == 'today':
        cv_list = cv_list.filter(uploaded_at__date=now.date())
    elif date_filter == 'week':
        cv_list = cv_list.filter(uploaded_at__gte=now - timedelta(days=7))
    elif date_filter == 'month':
        cv_list = cv_list.filter(uploaded_at__gte=now - timedelta(days=30))

    # إعداد ملف التصدير
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="cv_database_export.csv"'
    writer = csv.writer(response)
    
    # كتابة العناوين
    writer.writerow(['Candidate Name', 'Email', 'Phone', 'Applied Job', 'Upload Date', 'AI Match Score', 'Top Skills'])

    # كتابة البيانات
    for cv in cv_list:
        candidate = cv.candidate
        skills = ", ".join([skill.skill_name for skill in candidate.skills.all()[:5]]) # استخراج أول 5 مهارات كنص
        score = f"{cv.match_result.overall_score}%" if hasattr(cv, 'match_result') else "Pending"
        
        writer.writerow([
            candidate.full_name or 'Unknown',
            candidate.email or 'N/A',
            candidate.phone or 'N/A',
            cv.job.title,
            cv.uploaded_at.strftime('%Y-%m-%d'),
            score,
            skills
        ])

    return response