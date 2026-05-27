import csv
from django.http import HttpResponse
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
            success_count = 0
            error_count = 0

        for file in cv_files:
            try:
                # استخدام transaction لضمان عدم حفظ بيانات ناقصة في حال حدوث خطأ
                with transaction.atomic():
                    # أ. إنشاء مرشح وملف سيرة ذاتية فارغ مبدئياً
                    candidate = Candidate.objects.create()
                    cv_instance = CV.objects.create(
                        candidate=candidate, 
                        job=job, 
                        file_path=file, 
                        status='pending'
                    )

                    # ب. تمرير مسار الملف الحقيقي لمحرك الذكاء الاصطناعي
                    # ملاحظة: .path تعطي المسار الكامل على القرص الصلب
                    extracted_data = parse_single_cv(cv_instance.file_path.path)

                    # ج. تحديث بيانات المرشح الأساسية
                    candidate.full_name = extracted_data.get('name') or f"Candidate #{candidate.id}"
                    candidate.email = extracted_data.get('email')
                    candidate.phone = extracted_data.get('mobile')
                    candidate.save()

                    # د. حفظ البيانات المستخرجة في جدول ParsedData
                    ParsedData.objects.create(
                        cv=cv_instance,
                        raw_text=extracted_data.get('raw_text', ''),
                        gpa=extracted_data.get('gpa'),
                        degree=extracted_data.get('education', {}).get('degree'),
                        universities=extracted_data.get('education', {}).get('universities', []),
                        workplaces=extracted_data.get('experience', {}).get('workplaces', []),
                        projects=extracted_data.get('projects', {}).get('names', [])
                    )

                    # هـ. حفظ مهارات المرشح
                    cand_skills_list = extracted_data.get('skills', [])
                    for skill_name in cand_skills_list:
                        CandidateSkill.objects.get_or_create(
                            candidate=candidate, 
                            skill_name=skill_name.title()
                        )

                    # و. خوارزمية حساب المطابقة (Match Scoring Engine)
                    job_skills_set = {s.skill_name.lower() for s in skills}
                    cand_skills_set = {s.lower() for s in cand_skills_list}
                    
                    # حساب درجة المهارات (40%)
                    if job_skills_set:
                        matched_skills = job_skills_set.intersection(cand_skills_set)
                        skills_score = (len(matched_skills) / len(job_skills_set)) * 100
                    else:
                        skills_score = 100.0

                    # حساب درجة الخبرة (25%) تقريبية بناءً على عدد أماكن العمل
                    workplaces = extracted_data.get('experience', {}).get('workplaces', [])
                    exp_score = min(100.0, len(workplaces) * 30.0) if job.min_experience > 0 else 100.0

                    # حساب درجة التعليم (15%)
                    edu_score = 100.0 if extracted_data.get('education', {}).get('degree') else 60.0

                    # الدرجة النهائية
                    overall_score = (skills_score * 0.40) + (exp_score * 0.25) + (edu_score * 0.15) + (85.0 * 0.20) # 20% ثابتة حالياً للمشاريع واللغات

                    ai_summary = f"System extracted {len(cand_skills_list)} skills. Candidate matched {len(matched_skills) if job_skills_set else 0} out of {len(job_skills_set)} core technical requirements."

                    MatchResult.objects.create(
                        cv=cv_instance,
                        job=job,
                        overall_score=round(overall_score, 1),
                        skills_score=round(skills_score, 1),
                        experience_score=round(exp_score, 1),
                        education_score=round(edu_score, 1),
                        ai_summary=ai_summary
                    )

                    # تغيير حالة الملف إلى مكتمل
                    cv_instance.status = 'completed'
                    cv_instance.save()
                    
                    success_count += 1

            except Exception as e:
                error_count += 1
                print(f"[SYSTEM ERROR] Failed to process CV: {e}")
                # في حال حدوث خطأ، نقوم بتحديث حالة الـ CV إلى failed
                if 'cv_instance' in locals():
                    cv_instance.status = 'failed'
                    cv_instance.save()

        # إرسال تنبيه للمستخدم بنتيجة العملية
        if success_count > 0:
            messages.success(request, f"Successfully processed {success_count} CV(s) through the AI Engine.")
        if error_count > 0:
            messages.error(request, f"Failed to process {error_count} CV(s). Please ensure they are valid PDF/DOCX files.")
            
        # إعادة توجيه لنفس الصفحة لتحديث الجدول
        return redirect('job_detail', job_id=job.id)

    # 3. جلب نتائج الذكاء الاصطناعي (المرشحين) لهذه الوظيفة، مرتبة من الأعلى للأقل (للـ GET Request)
    matches = MatchResult.objects.filter(job=job).select_related('cv__candidate').order_by('-overall_score')
    
    context = {
        'job': job,
        'skills': skills,
        'matches': matches,
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

