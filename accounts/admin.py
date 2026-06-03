from django.contrib import admin
from django.contrib.auth.hashers import make_password # استيراد دالة التشفير
from .models import User

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'first_name', 'last_name', 'is_staff', 'is_active', 'created_at')
    list_filter = ('is_staff', 'is_active')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('-created_at',)

    # هذه الدالة تتدخل قبل الحفظ لتشفير كلمة المرور
    def save_model(self, request, obj, form, change):
        # التحقق مما إذا كانت كلمة المرور موجودة ولم يتم تشفيرها مسبقاً
        if obj.password and not obj.password.startswith('pbkdf2_'):
            obj.password = make_password(obj.password)
        
        # إكمال عملية الحفظ الطبيعية
        super().save_model(request, obj, form, change)