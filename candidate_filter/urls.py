from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.conf import settings             # أضف هذا السطر
from django.conf.urls.static import static   # وأضف هذا السطر

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', RedirectView.as_view(pattern_name='login', permanent=False), name='home'),
    
    path('', include('accounts.urls')),
    path('jobs/', include('jobs.urls')),
    path('cvs/', include('cvs.urls')),
    path('parsing/', include('parsing.urls')),
    path('ai_engine/', include('ai_engine.urls')),
    path('matching/', include('matching.urls')),
    path('dashboard/', include('dashboard.urls')),
]

# أضف هذا الشرط في نهاية الملف لكي يعمل عرض الملفات أثناء وضع التطوير
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)