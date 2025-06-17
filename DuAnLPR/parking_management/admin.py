from django.contrib import admin
from .models import KhachThue, VehicleTypes, Vehicle, MonthlyTicketRules, PerTurnTicketRules, ParkingHistory

class VehicleAdmin(admin.ModelAdmin):
    list_display = ('BienSoXe', 'KhachThueID', 'VehicleTypeID') # ĐÃ XÓA
    list_filter = ('VehicleTypeID', 'KhachThueID__HoVaTen') # ĐÃ XÓA
    search_fields = ('BienSoXe', 'KhachThueID__HoVaTen')
class KhachThueAdmin(admin.ModelAdmin):
    list_display = ('HoVaTen', 'SoDienThoai', 'GioiTinh', 'NgaySinh')
    search_fields = ('HoVaTen', 'SoDienThoai')

class ParkingHistoryAdmin(admin.ModelAdmin):
    list_display = ('RecordID', 'get_bien_so_xe', 'EntryTime', 'ExitTime', 'CalculatedFee', 'Status', 'WasMonthlyTicketUsed')
    list_filter = ('Status', 'WasMonthlyTicketUsed', 'EntryTime')
    search_fields = ('ProcessedLicensePlateEntry', 'VehicleID__BienSoXe')

    def get_bien_so_xe(self, obj):
        if obj.VehicleID:
            return obj.VehicleID.BienSoXe
        return obj.ProcessedLicensePlateEntry
    get_bien_so_xe.short_description = 'Biển Số Xe'


# Đăng ký các model
admin.site.register(KhachThue, KhachThueAdmin)
admin.site.register(VehicleTypes) # Có thể tạo ModelAdmin riêng nếu muốn tùy chỉnh
admin.site.register(Vehicle, VehicleAdmin) # Sử dụng VehicleAdmin đã tùy chỉnh
admin.site.register(MonthlyTicketRules)
admin.site.register(PerTurnTicketRules)
admin.site.register(ParkingHistory, ParkingHistoryAdmin)