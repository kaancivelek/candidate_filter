import csv
import threading
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Count, Q
# استيراد النماذج من التطبيقات المختلفة
from .models import Job, JobSkill
from cvs.models import Candidate, CV
from parsing.models import ParsedData, CandidateSkill
from matching.models import MatchResult

# استيراد محرك الذكاء الاصطناعي
from parsing.cv_parser import parse_single_cv


def _process_cv_in_background(cv_id, job_id):
    """
    Arka planda çalışan CV işleme fonksiyonu.
    Django ORM'yi thread-safe şekilde kullanmak için her işlemde
    bağlantıyı açıp kapatır.
    """
    from django.db import connection
    try:
        # Thread içinde taze DB bağlantısı kullan
        cv_instance = CV.objects.select_related('candidate', 'job').get(id=cv_id)
        job = cv_instance.job
        candidate = cv_instance.candidate
        skills = list(job.required_skills.all())

        print(f"[ASYNC] CV {cv_id} işleniyor...")

        # NLP ile CV metnini çıkar ve analiz et
        extracted_data = parse_single_cv(cv_instance.file_path.path)

        # Aday bilgilerini güncelle
        candidate.full_name = extracted_data.get('name') or f"Candidate #{candidate.id}"
        candidate.email = extracted_data.get('email')
        candidate.phone = extracted_data.get('mobile')
        candidate.save()

        # ParsedData kaydet
        ParsedData.objects.create(
            cv=cv_instance,
            raw_text=extracted_data.get('raw_text', ''),
            gpa=extracted_data.get('gpa'),
            degree=extracted_data.get('education', {}).get('degree'),
            universities=extracted_data.get('education', {}).get('universities', []),
            workplaces=extracted_data.get('experience', {}).get('workplaces', []),
            projects=extracted_data.get('projects', {}).get('names', [])
        )

        # Aday becerilerini kaydet
        cand_skills_list = extracted_data.get('skills', [])
        for skill_name in cand_skills_list:
            CandidateSkill.objects.get_or_create(
                candidate=candidate,
                skill_name=skill_name.title()
            )

        # Puan hesapla
        job_skills_set = {s.skill_name.lower() for s in skills}
        cand_skills_set = {s.lower() for s in cand_skills_list}

        if job_skills_set:
            matched_skills = job_skills_set.intersection(cand_skills_set)
            skills_score = (len(matched_skills) / len(job_skills_set)) * 100
        else:
            matched_skills = set()
            skills_score = 100.0

        workplaces = extracted_data.get('experience', {}).get('workplaces', [])
        exp_score = min(100.0, len(workplaces) * 30.0) if job.min_experience > 0 else 100.0
        edu_score = 100.0 if extracted_data.get('education', {}).get('degree') else 60.0
        overall_score = (skills_score * 0.40) + (exp_score * 0.25) + (edu_score * 0.15) + (85.0 * 0.20)

        ai_summary = (
            f"System extracted {len(cand_skills_list)} skills. "
            f"Candidate matched {len(matched_skills)} out of {len(job_skills_set)} core technical requirements."
        )

        MatchResult.objects.create(
            cv=cv_instance,
            job=job,
            overall_score=round(overall_score, 1),
            skills_score=round(skills_score, 1),
            experience_score=round(exp_score, 1),
            education_score=round(edu_score, 1),
            ai_summary=ai_summary
        )

        cv_instance.status = 'completed'
        cv_instance.save()
        print(f"[ASYNC] CV {cv_id} başarıyla tamamlandı.")

    except Exception as e:
        import traceback
        print(f"[ASYNC ERROR] CV {cv_id} işlenirken hata:\n{traceback.format_exc()}")
        try:
            cv_obj = CV.objects.get(id=cv_id)
            cv_obj.status = 'failed'
            cv_obj.save()
        except Exception:
            pass
    finally:
        # Thread bittikten sonra DB bağlantısını kapat (connection leak'i önle)
        connection.close()


@login_required
def cv_processing_status(request, job_id):
    """
    AJAX endpoint: İş için beklemedeki ve tamamlanan CV sayılarını döner.
    Frontend'in sayfayı otomatik yenilemesi için polling yapar.
    """
    job = get_object_or_404(Job, id=job_id)
    pending = CV.objects.filter(job=job, status='pending').count()
    completed = CV.objects.filter(job=job, status='completed').count()
    failed = CV.objects.filter(job=job, status='failed').count()
    return JsonResponse({
        'pending': pending,
        'completed': completed,
        'failed': failed,
        'is_processing': pending > 0,
    })


@login_required
def job_list(request):

    # 1. التقاط متغيرات البحث والفلترة من الرابط (GET Parameters)
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', 'all')
    sort_by = request.GET.get('sort', 'newest')

    # 2. بناء الاستعلام الأساسي مع الحسابات (إجمالي السير الذاتية، والمرشحين المختارين)
    jobs = Job.objects.annotate(
        total_cvs=Count('received_cvs', distinct=True),
        shortlisted_cvs=Count(
            'received_cvs', 
            filter=Q(received_cvs__match_result__overall_score__gte=80.0), 
            distinct=True
        )
    )

    # 3. تطبيق فلتر البحث النصي (في العنوان أو القسم)
    if search_query:
        jobs = jobs.filter(
            Q(title__icontains=search_query) | 
            Q(department__icontains=search_query)
        )

    # 4. تطبيق فلتر الحالة (Active أو Closed)
    if status_filter in ['active', 'closed']:
        jobs = jobs.filter(status=status_filter)

    # 5. تطبيق الترتيب (الأحدث أو الأقدم)
    if sort_by == 'oldest':
        jobs = jobs.order_by('created_at')
    else:
        jobs = jobs.order_by('-created_at') # الأحدث هو الافتراضي

    # 6. تمرير البيانات الحالية للواجهة للحفاظ على الفلاتر المختارة بعد التحديث
    context = {
        'jobs': jobs,
        'search_query': search_query,
        'status_filter': status_filter,
        'sort_by': sort_by,
    }
    
    return render(request, 'jobs/job_list.html', context)

@login_required
def job_form(request):
    if request.method == 'POST':
        # 1. استخراج البيانات من النموذج
        title = request.POST.get('title')
        department = request.POST.get('department')
        experience = request.POST.get('experience')
        education = request.POST.get('education')
        skills_raw = request.POST.get('skills')
        description = request.POST.get('description')

        # 2. التحقق من وجود البيانات الأساسية
        if title and department and experience and education and skills_raw:
            # 3. إنشاء وحفظ الوظيفة في جدول Job
            job = Job.objects.create(
                created_by=request.user,
                title=title,
                department=department,
                min_experience=int(experience),
                education_level=education,
                description=description,
                status=request.POST.get('status', 'active') # <--- أضفنا هذا السطر لاستقبال الحالة
            )
            # 4. معالجة المهارات: تقسيم النص وحفظ كل مهارة في جدول JobSkill
            # نقوم بتقسيم النص عند كل فاصلة، وإزالة المسافات الزائدة
            skills_list = [skill.strip() for skill in skills_raw.split(',') if skill.strip()]
            for skill_name in skills_list:
                JobSkill.objects.create(job=job, skill_name=skill_name)

            # 5. إرسال رسالة نجاح والعودة لقائمة الوظائف
            messages.success(request, f"Job '{title}' has been successfully created!")
            return redirect('job_list')
        else:
            messages.error(request, "Please fill in all required fields.")

    return render(request, 'jobs/job_form.html')

@login_required
def job_detail(request, job_id):
    # 1. جلب الوظيفة والمهارات المطلوبة
    job = get_object_or_404(Job, id=job_id)
    skills = job.required_skills.all()

    # 2. معالجة الطلبات القادمة من الواجهة (POST Requests)
    if request.method == 'POST':
        
        # أ. التحقق مما إذا كان الطلب هو "تغيير حالة الوظيفة"
        if 'toggle_status' in request.POST:
            job.status = 'closed' if job.status == 'active' else 'active'
            job.save()
            status_word = "Activated" if job.status == 'active' else "Closed"
            messages.success(request, f"Job has been successfully {status_word}.")
            return redirect('job_detail', job_id=job.id)

        # ب. التحقق مما إذا كان الطلب هو "رفع سير ذاتية"
        elif request.FILES.getlist('cv_files'):
            cv_files = request.FILES.getlist('cv_files')
            queued_count = 0

            for file in cv_files:
                try:
                    # 1. احفظ الملف وأنشئ سجلات فارغة فوراً (لا NLP هنا)
                    with transaction.atomic():
                        candidate = Candidate.objects.create()
                        cv_instance = CV.objects.create(
                            candidate=candidate,
                            job=job,
                            file_path=file,
                            status='pending'
                        )
                    queued_count += 1

                    # 2. ابدأ معالجة هذا الـ CV في thread منفصل (لا تنتظر)
                    t = threading.Thread(
                        target=_process_cv_in_background,
                        args=(cv_instance.id, job.id),
                        daemon=True
                    )
                    t.start()

                except Exception as e:
                    print(f"[SYSTEM ERROR] CV kayıt edilemedi: {e}")

            if queued_count > 0:
                messages.success(
                    request,
                    f"{queued_count} CV başarıyla kuyruğa alındı. İşlem arka planda devam ediyor, sayfayı yenileyerek sonuçları görebilirsiniz."
                )

        return redirect('job_detail', job_id=job.id)

    # 3. جلب نتائج الذكاء الاصطناعي (المرشحين) لهذه الوظيفة، مرتبة من الأعلى للأقل (للـ GET Request)
    matches = MatchResult.objects.filter(job=job).select_related('cv__candidate').order_by('-overall_score')
    pending_count = CV.objects.filter(job=job, status='pending').count()

    context = {
        'job': job,
        'skills': skills,
        'matches': matches,
        'pending_count': pending_count,
    }
    
    return render(request, 'jobs/job_detail.html', context)


@login_required
def export_candidates(request, job_id):
    # 1. جلب الوظيفة والمرشحين المرتبطين بها مرتبين حسب أعلى درجة
    job = get_object_or_404(Job, id=job_id)
    matches = MatchResult.objects.filter(job=job).select_related('cv__candidate').order_by('-overall_score')

    # 2. إعداد استجابة ديجانغو لتكون على شكل ملف CSV للتحميل
    response = HttpResponse(content_type='text/csv')
    # تسمية الملف باسم الوظيفة
    file_name = f"candidates_job_{job.id}.csv"
    response['Content-Disposition'] = f'attachment; filename="{file_name}"'

    # 3. إنشاء كاتب البيانات (Writer)
    writer = csv.writer(response)
    
    # 4. كتابة صف العناوين (الهيدر) في ملف الإكسل
    writer.writerow(['Rank', 'Candidate Name', 'Email', 'Phone Number', 'Experience Match', 'Overall AI Score'])

    # 5. المرور على المرشحين وكتابة بياناتهم صفا بصف
    for index, match in enumerate(matches, 1):
        candidate = match.cv.candidate
        writer.writerow([
            index,  # الترتيب
            candidate.full_name or 'Unknown',
            candidate.email or 'No email',
            candidate.phone or 'No phone',
            f"{match.experience_score}%",
            f"{match.overall_score}%"
        ])

    return response


@login_required
def job_edit(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    
    # جلب المهارات الحالية وتحويلها إلى نص مفصول بفواصل ليظهر في الحقل
    current_skills = ", ".join([skill.skill_name for skill in job.required_skills.all()])

    if request.method == 'POST':
        # تحديث بيانات الوظيفة
        job.title = request.POST.get('title')
        job.department = request.POST.get('department')
        job.min_experience = int(request.POST.get('experience'))
        job.education_level = request.POST.get('education')
        job.description = request.POST.get('description')
        job.status = request.POST.get('status', 'active') # <--- أضفنا هذا السطر هنا أيضاً
        job.save()

        # تحديث المهارات: نقوم بحذف المهارات القديمة وإضافة الجديدة
        skills_raw = request.POST.get('skills')
        job.required_skills.all().delete()
        
        skills_list = [skill.strip() for skill in skills_raw.split(',') if skill.strip()]
        for skill_name in skills_list:
            JobSkill.objects.create(job=job, skill_name=skill_name)

        messages.success(request, f"Job '{job.title}' updated successfully!")
        return redirect('job_detail', job_id=job.id)

    context = {
        'job': job,
        'current_skills': current_skills,
        'is_edit': True # نمرر هذا المتغير لنعرف في الـ HTML أننا في وضع التعديل
    }
    # نستخدم نفس صفحة الإنشاء (job_form.html)
    return render(request, 'jobs/job_form.html', context)

