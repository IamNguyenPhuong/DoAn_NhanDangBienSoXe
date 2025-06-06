from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
# Thêm dòng import này
from django.views.generic.base import RedirectView

urlpatterns = [
    # Dòng này sẽ chuyển hướng từ trang gốc sang /parking/
    path('', RedirectView.as_view(url='/parking/', permanent=False)),

    path('admin/', admin.site.urls),
    path('parking/', include('parking_management.urls')),
]

# Phục vụ file media (ảnh do người dùng upload)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Phục vụ file static (logo, css, js)
urlpatterns += staticfiles_urlpatterns()