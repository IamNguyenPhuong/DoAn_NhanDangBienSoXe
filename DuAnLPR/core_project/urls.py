from django.contrib import admin
from django.urls import path, include
from django.conf import settings # Thêm dòng này
from django.conf.urls.static import static # Thêm dòng này

urlpatterns = [
    path('admin/', admin.site.urls),
    path('parking/', include('parking_management.urls')),
]

# Thêm dòng này để phục vụ media files trong môi trường development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)