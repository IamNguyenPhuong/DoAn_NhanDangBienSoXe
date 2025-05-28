from django.urls import path
from . import views

app_name = 'parking_management'

urlpatterns = [
    path('kiem-tra-bien-so/', views.kiem_tra_bien_so_view, name='kiem_tra_bien_so'),
    path('xe-ra/', views.xe_ra_khoi_bai_view, name='xe_ra_khoi_bai'), # THÊM DÒNG NÀY
]