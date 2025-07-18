from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.utils import timezone

# Hàm kiểm tra số điện thoạ
phone_regex = RegexValidator(
    regex=r'^0\d{9}$',
    message="Số điện thoại phải bắt đầu bằng số 0 và có đủ 10 chữ số."
)

# 1. Bảng Admin - Chúng ta sẽ sử dụng hệ thống User tích hợp của Django sau này
#   nếu cần tùy biến. Tạm thời không tạo model Admin riêng ở đây để tránh
#   xung đột với hệ thống admin có sẵn của Django. Bạn sẽ tạo superuser
#   của Django để đăng nhập vào trang quản trị.

# 2. Bảng KhachThue (Khách Thuê/Cư Dân)
class KhachThue(models.Model):
    KhachThueID = models.AutoField(primary_key=True)
    HoVaTen = models.CharField(max_length=255)
    NgaySinh = models.DateField()
    GIOI_TINH_CHOICES = [
        ('Nam', 'Nam'),
        ('Nữ', 'Nữ'),
    ]
    GioiTinh = models.CharField(max_length=10, choices=GIOI_TINH_CHOICES)

    # Bỏ null=True, blank=True và thêm validators
    SoDienThoai = models.CharField(
        max_length=10,  # Giới hạn độ dài trong CSDL là 10
        validators=[phone_regex],  # Áp dụng quy tắc kiểm tra
        unique = True
    )

    def __str__(self):
        return self.HoVaTen

    class Meta:
        db_table = 'KhachThue'


# 3. Bảng VehicleTypes (Loại Xe)
class VehicleTypes(models.Model):
    VehicleTypeID = models.AutoField(primary_key=True)
    TypeName = models.CharField(max_length=100, unique=True)  # VD: 'Xe máy', 'Ô tô'

    def __str__(self):
        return self.TypeName

    class Meta:
        db_table = 'VehicleTypes'


# 4. Bảng Vehicle (Xe Đăng Ký của Khách Thuê)
class Vehicle(models.Model):
    VehicleID = models.AutoField(primary_key=True)
    KhachThueID = models.ForeignKey(KhachThue, on_delete=models.CASCADE)
    VehicleTypeID = models.ForeignKey(VehicleTypes, on_delete=models.RESTRICT)
    BienSoXe = models.CharField(max_length=15, unique=True, verbose_name="Biển số xe")


    def __str__(self):
        return f"{self.BienSoXe} - {self.KhachThueID.HoVaTen}"

    class Meta:
        db_table = 'vehicle'
        verbose_name = "Xe"
        verbose_name_plural = "Quản lý xe"


    @property
    def has_active_monthly_ticket(self):
        """
        Phương thức kiểm tra xem xe này có vé tháng nào đang còn hiệu lực hay không.
        Trả về True nếu có, False nếu không.
        """
        today = timezone.now().date()
        # Dùng .exists() để tối ưu, chỉ cần biết có tồn tại hay không, không cần lấy dữ liệu
        # Dòng dưới đây đã được sửa lại để truy vấn đúng cách
        return GhiNhanVeThang.objects.filter(vehicle=self, expiry_date__gte=today).exists()




# 5. Bảng MonthlyTicketRules (Quy Tắc Giá Vé Tháng)
class MonthlyTicketRules(models.Model):
    MonthlyRuleID = models.AutoField(primary_key=True)
    # 1. Đảm bảo mỗi loại xe chỉ có 1 quy tắc giá
    VehicleTypeID = models.OneToOneField(VehicleTypes, on_delete=models.CASCADE)
    # 2. Đổi giá vé về kiểu số nguyên
    PricePerMonth = models.PositiveIntegerField(default=0)

    def __str__(self):
        # ... (phần này có thể giữ nguyên hoặc chỉnh sửa nếu muốn)
        vehicle_type_name = self.VehicleTypeID.TypeName if self.VehicleTypeID else "Unknown Type"
        return f"Vé tháng cho {vehicle_type_name} - {self.PricePerMonth} VND"

    class Meta:
        db_table = 'MonthlyTicketRules'


# 6. Bảng PerTurnTicketRules (Quy Tắc Giá Vé Lượt)
class PerTurnTicketRules(models.Model):
    PerTurnRuleID = models.AutoField(primary_key=True)
    VehicleTypeID = models.ForeignKey(VehicleTypes, on_delete=models.RESTRICT)
    Price = models.PositiveIntegerField(default=0)
    ShiftName = models.CharField(max_length=100, null=True, blank=True)  # VD: 'Sáng', 'Chiều'
    TimeFrom = models.TimeField(null=True, blank=True)
    TimeTo = models.TimeField(null=True, blank=True)

    def __str__(self):
        vehicle_type_name = self.VehicleTypeID.TypeName if self.VehicleTypeID else "Unknown Type"
        shift_name = self.ShiftName if self.ShiftName else "Cả ngày"
        return f"Vé lượt {shift_name} cho {vehicle_type_name} - {self.Price} VND"

    class Meta:
        db_table = 'PerTurnTicketRules'


# 7. Bảng ParkingHistory (Lịch Sử Ra/Vào) - Phiên bản cuối cùng
class ParkingHistory(models.Model):
    RecordID = models.AutoField(primary_key=True)
    VehicleID = models.ForeignKey(Vehicle, on_delete=models.SET_NULL, null=True, blank=True)
    VehicleTypeID = models.ForeignKey(VehicleTypes, on_delete=models.SET_NULL, null=True, blank=True,
                                      verbose_name="Loại xe lúc vào")
    EntryTime = models.DateTimeField(auto_now_add=True)
    ExitTime = models.DateTimeField(null=True, blank=True)
    ProcessedLicensePlateEntry = models.CharField(max_length=50, null=True, blank=True)
    ProcessedLicensePlateExit = models.CharField(max_length=50, null=True, blank=True)
    EntryVehicleImagePath = models.CharField(max_length=255, null=True, blank=True)
    ExitVehicleImagePath = models.CharField(max_length=255, null=True, blank=True)

    # --- THAY ĐỔI Ở ĐÂY ---
    CalculatedFee = models.PositiveIntegerField(null=True, blank=True, default=0)

    # PerTurnRuleAppliedID đã bị xóa
    WasMonthlyTicketUsed = models.BooleanField(default=False)

    STATUS_CHOICES = [
        ('IN_YARD', 'Đang trong bãi'),
        ('EXITED', 'Đã rời bãi'),
    ]
    Status = models.CharField(max_length=50, choices=STATUS_CHOICES, null=True, blank=True)

    def __str__(self):
        vehicle_plate = ""
        if self.VehicleID:
            vehicle_plate = self.VehicleID.BienSoXe
        elif self.ProcessedLicensePlateEntry:
            vehicle_plate = self.ProcessedLicensePlateEntry
        else:
            vehicle_plate = "Unknown Vehicle"
        return f"Lượt {self.RecordID} - Xe {vehicle_plate}"

    class Meta:
        db_table = 'ParkingHistory'

class GhiNhanVeThang(models.Model):
    """Lưu lại lịch sử các giao dịch mua vé tháng."""
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, verbose_name="Xe đăng ký")
    purchase_date = models.DateField(auto_now_add=True, verbose_name="Ngày mua")
    expiry_date = models.DateField(verbose_name="Ngày hết hạn")
    price = models.PositiveIntegerField(verbose_name="Số tiền đã trả")

    def __str__(self):
        return f"Vé tháng cho {self.vehicle.BienSoXe} - Hạn: {self.expiry_date.strftime('%d/%m/%Y')}"

    class Meta:
        verbose_name = "Ghi nhận vé tháng"
        verbose_name_plural = "Các ghi nhận vé tháng"
        ordering = ['-purchase_date']

