from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth import get_user_model,logout
from .forms import ProfileUpdateForm, CustomPasswordChangeForm
from django.urls import reverse
from django.core.mail import send_mail
from django.conf import settings

User = get_user_model()

def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        remember = request.POST.get('remember') # التقاط قيمة "تذكرني"
        
        user = authenticate(request, email=email, password=password)
        if user is not None:
            auth_login(request, user)
            
            # --- تفعيل ميزة "تذكرني" ---
            if remember:
                # حفظ الجلسة لمدة أسبوعين (1209600 ثانية)
                request.session.set_expiry(1209600)
            else:
                # إنهاء الجلسة بمجرد إغلاق المتصفح (0)
                request.session.set_expiry(0)
                
            return redirect('dashboard')
        else:
            messages.error(request, "Invalid email or password.")
            
    return render(request, 'accounts/login.html')


def logout_view(request):
    # 1. تنفيذ عملية تسجيل الخروج الفعلية
    logout(request)
    
    # 2. (اختياري) إرسال رسالة للمستخدم
    messages.info(request, "You have been successfully logged out.")
    
    # 3. توجيه المستخدم إلى صفحة تسجيل الدخول
    return redirect('login')


@login_required
def profile_view(request):
    if request.method == 'POST':
        # معالجة تحديث بيانات الملف الشخصي
        if 'update_profile' in request.POST:
            request.user.first_name = request.POST.get('first_name')
            request.user.last_name = request.POST.get('last_name')
            request.user.save()
            messages.success(request, 'Your profile has been updated successfully.')
            return redirect('profile')

        # معالجة تغيير كلمة المرور
        elif 'change_password' in request.POST:
            old_password = request.POST.get('old_password')
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')

            # 1. التحقق من صحة كلمة المرور القديمة
            if not request.user.check_password(old_password):
                messages.error(request, 'Your current password was entered incorrectly.')
            
            # 2. التحقق من الطول (طبقة حماية إضافية للباكيند)
            elif len(new_password) < 8:
                messages.error(request, 'The new password must be at least 8 characters long.')
            
            # 3. التحقق من تطابق الكلمتين
            elif new_password != confirm_password:
                messages.error(request, 'The two new password fields didn’t match.')
            
            # 4. حفظ كلمة المرور الجديدة
            else:
                request.user.set_password(new_password)
                request.user.save()
                # إبقاء المستخدم مسجلاً للدخول بعد تغيير كلمة المرور
                update_session_auth_hash(request, request.user)
                
                # إرسال رسالة النجاح
                messages.success(request, 'Your password was successfully updated!')
                return redirect('profile')

    return render(request, 'accounts/profile.html')


# --- إدارة استعادة كلمة المرور (Password Reset Cycle) ---

def password_reset_request(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        associated_users = User.objects.filter(email=email)
        
        if associated_users.exists():
            for user in associated_users:
                # 1. توليد التوكن ومعرف المستخدم
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                token = default_token_generator.make_token(user)
                
                # 2. بناء الرابط الفعلي لصفحة التأكيد
                reset_link = request.build_absolute_uri(
                    reverse('password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
                )
                
                # 3. إعداد وإرسال البريد الإلكتروني الفعلي
                subject = "Password Reset Request - Intelligent Cloud HR"
                message = f"""Hello {user.first_name or user.username},

We received a request to reset your password for your Intelligent Cloud HR account.
Please click the link below to set a new password:

{reset_link}

If you didn't request this, you can safely ignore this email.

Best regards,
HR System Administrator
"""
                try:
                    send_mail(
                        subject=subject,
                        message=message,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[user.email],
                        fail_silently=False,
                    )
                except Exception as e:
                    print(f"[EMAIL ERROR] Failed to send email: {e}")
                
            return redirect('password_reset_done')
        else:
            return redirect('password_reset_done')
            
    return render(request, 'accounts/password_reset.html')


def password_reset_done(request):
    return render(request, 'accounts/password_reset_done.html')


def password_reset_confirm(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        validlink = True
        if request.method == 'POST':
            form = SetPasswordForm(user, request.POST)
            if form.is_valid():
                form.save()
                return redirect('password_reset_complete')
        else:
            form = SetPasswordForm(user)
    else:
        validlink = False
        form = None

    context = {
        'form': form,
        'validlink': validlink
    }
    return render(request, 'accounts/password_reset_confirm.html', context)


def password_reset_complete(request):
    return render(request, 'accounts/password_reset_complete.html')