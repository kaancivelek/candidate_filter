from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import MatchResult
from parsing.models import ParsedData # لا تنسَ استيراد هذا النموذج

@login_required
def candidate_report(request, match_id):
    # جلب نتيجة التقييم
    match = get_object_or_404(MatchResult.objects.select_related('cv__candidate', 'job'), id=match_id)
    
    # جلب البيانات الخام التي استخرجها البارسير لعرضها في التفاصيل
    try:
        parsed_data = ParsedData.objects.get(cv=match.cv)
    except ParsedData.DoesNotExist:
        parsed_data = None
        
    job_skills_qs = match.job.required_skills.all()
    job_skills_dict = {skill.skill_name.lower(): skill.skill_name for skill in job_skills_qs}
    
    # جلب جميع مهارات المرشح
    candidate_skills_qs = match.cv.candidate.skills.all()
    all_candidate_skills = [skill.skill_name for skill in candidate_skills_qs]
    candidate_skills_dict = {skill.skill_name.lower(): skill.skill_name for skill in candidate_skills_qs}
    
    matched_skills = []
    missing_skills = []
    
    for skill_lower, original_name in job_skills_dict.items():
        if skill_lower in candidate_skills_dict:
            matched_skills.append(original_name)
        else:
            missing_skills.append(original_name)

    context = {
        'match': match,
        'parsed_data': parsed_data, # نمرر البيانات الخام هنا
        'matched_skills': matched_skills,
        'missing_skills': missing_skills,
        'all_candidate_skills': all_candidate_skills, # نمرر جميع المهارات هنا
    }
    
    return render(request, 'matching/candidate_report.html', context)