from django.contrib import admin
from .models import KhachThue, VehicleTypes, Vehicle, MonthlyTicketRules, PerTurnTicketRules, ParkingHistory

class VehicleAdmin(admin.ModelAdmin):
    list_display = ('BienSoXe', 'KhachThueID', 'VehicleTypeID', 'HasMonthlyTicket') # Các trường hiển thị trong danh sách
    list_filter = ('HasMonthlyTicket', 'VehicleTypeID', 'KhachThueID__HoVaTen') # Bộ lọc bên cạnh
    search_fields = ('BienSoXe', 'KhachThueID__HoVaTen') # Trường tìm kiếm
    list_editable = ('HasMonthlyTicket',) # Cho phép sửa trực tiếp HasMonthlyTicket từ danh sách
    # Để list_editable hoạt động, trường đó cũng phải có trong list_display

    # Nếu bạn muốn có action để set/unset HasMonthlyTicket cho nhiều xe cùng lúc
    actions = ['mark_as_monthly_ticket', 'unmark_as_monthly_ticket']

    def mark_as_monthly_ticket(self, request, queryset):
        queryset.update(HasMonthlyTicket=True)
    mark_as_monthly_ticket.short_description = "Đánh dấu là CÓ vé tháng"

    def unmark_as_monthly_ticket(self, request, queryset):
        queryset.update(HasMonthlyTicket=False)
    unmark_as_monthly_ticket.short_description = "Bỏ đánh dấu vé tháng (KHÔNG)"

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