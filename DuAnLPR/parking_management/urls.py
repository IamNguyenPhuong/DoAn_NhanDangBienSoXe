# parking_management/urls.py
from django.urls import path
from . import views

app_name = 'parking_management'

urlpatterns = [
    # ... (các URL hiện có của bạn: user_dashboard, login, logout, kiem_tra_bien_so, xe_ra_khoi_bai) ...
    path('', views.user_dashboard_view, name='user_dashboard'),
    path('login/', views.login_view, name='login_user'),
    path('logout/', views.logout_view, name='logout_user'),
    path('kiem-tra-bien-so/', views.kiem_tra_bien_so_view, name='kiem_tra_bien_so'),
    path('xe-ra/', views.xe_ra_khoi_bai_view, name='xe_ra_khoi_bai'),

    # URLs cho quản lý KhachThue
    path('khach-thue/', views.khachthue_list_view, name='khachthue_list'),
    path('khach-thue/them/', views.khachthue_create_view, name='khachthue_create'),
    path('khach-thue/sua/<int:khachthue_id>/', views.khachthue_update_view, name='khachthue_update'),
    path('khach-thue/xoa/<int:khachthue_id>/', views.khachthue_delete_view, name='khachthue_delete'),

    # URLs cho quản lý Vehicle
    path('xe/', views.vehicle_list_view, name='vehicle_list'),
    path('xe/them/', views.vehicle_create_view, name='vehicle_create'),
    path('xe/sua/<int:vehicle_id>/', views.vehicle_update_view, name='vehicle_update'),
    path('xe/xoa/<int:vehicle_id>/', views.vehicle_delete_view, name='vehicle_delete'),

    # URLs cho quản lý VehicleTypes
    path('loai-xe/', views.vehicletype_list_view, name='vehicletype_list'),
    path('loai-xe/them/', views.vehicletype_create_view, name='vehicletype_create'),
    path('loai-xe/sua/<int:vehicletype_id>/', views.vehicletype_update_view, name='vehicletype_update'),
    path('loai-xe/xoa/<int:vehicletype_id>/', views.vehicletype_delete_view, name='vehicletype_delete'),
# URLs cho quản lý MonthlyTicketRules
    path('gia-ve-thang/', views.monthlyticketrule_list_view, name='monthlyticketrule_list'),
    path('gia-ve-thang/them/', views.monthlyticketrule_create_view, name='monthlyticketrule_create'),
    path('gia-ve-thang/sua/<int:rule_id>/', views.monthlyticketrule_update_view, name='monthlyticketrule_update'),
    path('gia-ve-thang/xoa/<int:rule_id>/', views.monthlyticketrule_delete_view, name='monthlyticketrule_delete'),
# URLs cho quản lý PerTurnTicketRules
    path('gia-ve-luot/', views.perturnticketrule_list_view, name='perturnticketrule_list'),
    path('gia-ve-luot/them/', views.perturnticketrule_create_view, name='perturnticketrule_create'),
    path('gia-ve-luot/sua/<int:rule_id>/', views.perturnticketrule_update_view, name='perturnticketrule_update'),
    path('gia-ve-luot/xoa/<int:rule_id>/', views.perturnticketrule_delete_view, name='perturnticketrule_delete'),

    # URL cho xem Lịch sử Ra/Vào
    path('lich-su-ra-vao/', views.parkinghistory_list_view, name='parkinghistory_list'),
]