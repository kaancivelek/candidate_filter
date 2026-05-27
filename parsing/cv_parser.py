import os
import re
import traceback
import spacy
from spacy.matcher import Matcher
from django.conf import settings

# استيراد أدوات استخراج النص من المجلد الفرعي utils
from .utils import pdf2text
from .utils import doc2text

# كائنات عامة (Global instances) لتجنب إعادة تحميل النموذج مع كل سيرة ذاتية
nlp = None
skills_data_lower = None

def load_ai_models():
    """
    يقوم بتحميل نموذج spaCy وقاعدة بيانات المهارات مرة واحدة فقط في الذاكرة
    لضمان سرعة معالجة السير الذاتية.
    """
    global nlp, skills_data_lower

    if nlp is None:
        try:
            print("[AI ENGINE] Loading spaCy model...")
            nlp = spacy.load('en_core_web_sm')
        except Exception as e:
            print(f"[FATAL ERROR] spaCy yüklenemedi: {e}")
            raise

        # استخدام مسار ديجانغو الديناميكي للوصول لملف المهارات
        skills_path = os.path.join(settings.BASE_DIR, 'parsing', 'utils', 'skills_db.txt')
        print(f"[AI ENGINE] Loading skills from: {skills_path}")

        try:
            with open(skills_path, 'r', encoding='utf-8') as f:
                skills_data = f.read().splitlines()
            
            skills_data_lower = {
                str(skill).lower().strip(): str(skill).strip()
                for skill in skills_data if skill.strip()
            }
            print(f"[AI ENGINE] {len(skills_data_lower)} skill yüklendi.")
        except FileNotFoundError:
            print(f"[WARN] skills_db.txt bulunamadı: {skills_path}")
            skills_data_lower = {}


def extract_name(resume_text):
    """
    spaCy matcher ile isim çıkarır.
    """
    nlp_text = nlp(resume_text)
    
    # Her çağrıda yeni bir Matcher oluştur (global matcher yerine)
    local_matcher = Matcher(nlp.vocab)
    pattern = [{'POS': 'PROPN'}, {'POS': 'PROPN'}]
    local_matcher.add('NAME', patterns=[pattern])
    matches = local_matcher(nlp_text)

    for match_id, start, end in matches:
        span = nlp_text[start:end]
        if 'name' not in span.text.lower():
            return span.text
    return None


def extract_mobile_number(text):
    mob_num_regex = r'''(\+\d{1,3}[-\s]?)?(\(?\d{3}\)?[-\s.]?)(\d{3}[-\s.]?\d{4})'''
    phone = re.findall(re.compile(mob_num_regex), text)
    if phone:
        number = ''.join([''.join(p) for p in phone[:1]])
        number = re.sub(r'[\s\-\.]', '', number)
        return number if number else None
    return None


def extract_email(text):
    email_matches = re.findall(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", text)
    if email_matches:
        return email_matches[0].strip()
    return None


def extract_skills(resume_text):
    if not skills_data_lower:
        return []
    
    nlp_text = nlp(resume_text)
    tokens = [token.text for token in nlp_text if not token.is_stop]
    found = set()

    for chunk in nlp_text.noun_chunks:
        key = chunk.text.lower().strip()
        if key in skills_data_lower:
            found.add(skills_data_lower[key])

    for word in tokens:
        key = word.lower().strip()
        if key in skills_data_lower:
            found.add(skills_data_lower[key])

    return list(found)


def extract_gpa(text):
    gpa_regex = r'(?i)\b(?:gpa|c\.?g\.?p\.?a|not ortalaması)\b[\s:]*([0-4](?:\.\d{1,2})?(?:\s*/\s*[45](?:\.0)?)?)'
    matches = re.findall(gpa_regex, text)
    return matches[0].strip() if matches else None


def extract_section(text, start_keywords, end_keywords):
    lines = text.split('\n')
    section_text = []
    in_section = False

    for line in lines:
        upper_line = line.strip().upper()
        if not in_section:
            if any(kw in upper_line for kw in start_keywords) and len(upper_line.split()) < 5:
                in_section = True
        else:
            if any(kw in upper_line for kw in end_keywords) and len(upper_line.split()) < 5:
                break
            section_text.append(line)

    return "\n".join(section_text)


def extract_education_info(text):
    edu_keywords = ["EDUCATION", "EĞİTİM"]
    end_keywords = ["EXPERIENCE", "EMPLOYMENT", "SKILLS", "PROJECTS", "PROJECT",
                    "CERTIFICATIONS", "WORK HISTORY", "DENEYİM",
                    "YETENEKLER", "PROJELER", "İLGİ ALANLARI", "LEADERSHIP",
                    "ACTIVITIES", "INTERESTS"]

    edu_text = extract_section(text, edu_keywords, end_keywords)
    if not edu_text.strip():
        edu_text = text

    nlp_text = nlp(edu_text)
    unis = []

    for ent in nlp_text.ents:
        if ent.label_ == 'ORG' and any(
            w in ent.text.lower()
            for w in ['university', 'college', 'institute', 'üniversite', 'teknik']
        ):
            unis.append(ent.text)

    if not unis:
        matches = re.findall(
            r'(?i)[a-zA-ZçğıöşüÇĞİÖŞÜ\s]+(?:University|Institute|College|Üniversitesi)',
            edu_text
        )
        unis.extend([m.strip() for m in matches])

    degree = None
    degree_match = re.search(
        r'(?:B\.?Sc\.?|M\.?Sc\.?|B\.?A\.?|M\.?A\.?|Ph\.?D\.?|Bachelor|Master|Lisans|Yüksek Lisans)'
        r'(?:\s+in)?\s+([A-ZÇĞİÖŞÜa-zçğışöüü &]+(?:Engineering|Science|Arts|Computing|Technology|Mühendisliği|Bilgisayar)?)',
        edu_text, re.IGNORECASE
    )
    if degree_match:
        degree = degree_match.group(1).strip().rstrip('.')

    return {"universities": list(set(unis)), "degree": degree}


def extract_experience_info(text):
    exp_keywords = ["EXPERIENCE", "EMPLOYMENT", "WORK HISTORY", "DENEYİM",
                    "İŞ TECRÜBESİ", "WORK EXPERIENCE", "PROFESSIONAL EXPERIENCE"]
    end_keywords = ["EDUCATION", "EĞİTİM", "SKILLS", "PROJECTS", "PROJECT",
                    "CERTIFICATIONS", "YETENEKLER", "PROJELER", "İLGİ ALANLARI",
                    "REFERENCES", "LANGUAGES", "CERTIFICATES", "LEADERSHIP",
                    "ACTIVITIES", "INTERESTS"]

    exp_text = extract_section(text, exp_keywords, end_keywords)

    if not exp_text.strip():
        return [], []

    date_pattern = re.compile(
        r'\b(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?'
        r'|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?'
        r'|oca|şub|nis|haz|tem|ağu|eyl|eki|kas|ara)\w*\s+\d{4}'
        r'|\d{4}\s*[-–—]\s*(?:\d{4}|present|günümüz|halen|current)',
        re.IGNORECASE
    )

    workplaces = []
    lines = exp_text.split('\n')

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        if date_pattern.search(stripped):
            for offset in [2, 1]:
                if i - offset >= 0:
                    candidate = lines[i - offset].strip()
                    if (candidate
                            and not candidate.startswith(('•', '-', '*'))
                            and len(candidate.split()) <= 10
                            and candidate not in workplaces):
                        workplaces.append(candidate)
                        break

    exp_skills = extract_skills(exp_text)
    return workplaces, exp_skills


def extract_projects_info(text):
    proj_keywords = ["PROJECTS", "PROJECT", "PROJELER", "PROJE",
                     "PERSONAL PROJECTS", "ACADEMIC PROJECTS", "KEY PROJECTS"]
    end_keywords = ["EXPERIENCE", "EMPLOYMENT", "EDUCATION", "EĞİTİM", "SKILLS",
                    "CERTIFICATIONS", "YETENEKLER", "İLGİ ALANLARI",
                    "REFERENCES", "LANGUAGES", "CERTIFICATES", "LEADERSHIP",
                    "ACTIVITIES", "INTERESTS"]

    proj_text = extract_section(text, proj_keywords, end_keywords)

    if not proj_text.strip():
        return [], []

    project_names = []
    em_dash_pattern = re.compile(r'^([^—–\-\n]{2,40}?)\s*[—–]\s*', re.MULTILINE)
    for match in em_dash_pattern.finditer(proj_text):
        name = match.group(1).strip()
        if name and not name.startswith(('•', '-', '*')):
            project_names.append(name)

    if not project_names:
        for line in proj_text.split('\n'):
            stripped = line.strip()
            if (stripped
                    and stripped[0].isupper()
                    and len(stripped.split()) <= 8
                    and not stripped.startswith(('•', '-', '*'))):
                project_names.append(stripped)

    proj_keywords_found = extract_skills(proj_text)
    return list(dict.fromkeys(project_names)), proj_keywords_found


def parse_single_cv(file_path):
    """
    الدالة الرئيسية التي سيستدعيها ديجانغو لمعالجة سيرة ذاتية واحدة.
    تستقبل مسار الملف وتعيد قاموساً (Dictionary) بالبيانات المستخرجة.
    """
    load_ai_models()
    
    try:
        print(f"[INFO] İşleniyor: {file_path}")

        # تحديد نوع الملف لاستخدام الأداة المناسبة
        ext = file_path.lower().split('.')[-1]
        
        if ext == 'pdf':
            cv_text = pdf2text.get_Text(file_path)
        elif ext in ['doc', 'docx']:
            cv_text = doc2text.extract_text_from_doc(file_path)
        else:
            raise ValueError(f"Unsupported file format: {ext}")

        if not cv_text or not cv_text.strip():
            raise ValueError("empty_text")

        # معالجة واستخراج البيانات
        name                 = extract_name(cv_text)
        mobile               = extract_mobile_number(cv_text)
        email                = extract_email(cv_text)
        skills               = extract_skills(cv_text)
        gpa                  = extract_gpa(cv_text)
        education_info       = extract_education_info(cv_text)
        workplaces, exp_kws  = extract_experience_info(cv_text)
        project_names, pr_kws= extract_projects_info(cv_text)

        result = {
            "name": name,
            "mobile": mobile,
            "email": email,
            "gpa": gpa,
            "education": {
                "universities": education_info["universities"], 
                "degree": education_info["degree"]
            },
            "experience": {"workplaces": workplaces, "keywords": exp_kws},
            "projects": {"names": project_names, "keywords": pr_kws},
            "skills": skills,
            "raw_text": cv_text
        }
        
        print(f"[OK] Tamamlandı: {file_path}")
        return result

    except Exception as e:
        print(f"[ERROR] {file_path}:\n{traceback.format_exc()}")
        raise e