from django import forms
from .models import KhachThue, Vehicle, VehicleTypes, MonthlyTicketRules, PerTurnTicketRules
from datetime import datetime
# iamnguyenphuong/doan_nhandangbiensoxe/DoAn_NhanDangBienSoXe-ac4235a7a896f4f8dcec6ccd0440928a26a33a93/DuAnLPR/parking_management/forms.py

from django import forms
from .models import KhachThue #, các model khác
# ... các form khác

class KhachThueForm(forms.ModelForm):
    class Meta:
        model = KhachThue
        fields = ['HoVaTen', 'NgaySinh', 'GioiTinh', 'SoDienThoai']
        labels = {
            'HoVaTen': 'Họ và Tên',
            'NgaySinh': 'Ngày Sinh',
            'GioiTinh': 'Giới Tính',
            'SoDienThoai': 'Số Điện Thoại',
        }
        widgets = {
            'HoVaTen': forms.TextInput(attrs={'class': 'input', 'placeholder': 'Nhập họ và tên'}),
            'NgaySinh': forms.DateInput(attrs={'type': 'date', 'class': 'input'}),
            'GioiTinh': forms.Select(attrs={'class': 'input'}),
            'SoDienThoai': forms.TextInput(attrs={'class': 'input', 'placeholder': 'Nhập đúng 10 chữ số', 'type': 'tel'}),
        }

class VehicleForm(forms.ModelForm):
    class Meta:
        model = Vehicle
        fields = ['KhachThueID', 'BienSoXe', 'VehicleTypeID', 'HasMonthlyTicket']
        labels = {
            'KhachThueID': 'Chủ Sở Hữu (Khách Thuê)',
            'BienSoXe': 'Biển Số Xe',
            'VehicleTypeID': 'Loại Xe',
            'HasMonthlyTicket': 'Đăng Ký Vé Tháng',
        }
        widgets = {
            'BienSoXe': forms.TextInput(attrs={'class': 'input', 'placeholder': 'Ví dụ: 29A1-12345'}),
            'HasMonthlyTicket': forms.CheckboxInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Hiển thị tên khách thuê thay vì chỉ ID
        self.fields['KhachThueID'].label_from_instance = lambda obj: "%s (ID: %s)" % (obj.HoVaTen, obj.KhachThueID)
        # Hiển thị tên loại xe thay vì chỉ ID
        self.fields['VehicleTypeID'].label_from_instance = lambda obj: obj.TypeName


class VehicleTypeForm(forms.ModelForm):
    class Meta:
        model = VehicleTypes
        fields = ['TypeName']
        labels = {
            'TypeName': 'Tên Loại Xe',
        }
        widgets = {
            # Thêm 'class': 'input' vào đây
            'TypeName': forms.TextInput(attrs={'class': 'input', 'placeholder': 'Ví dụ: Xe máy, Ô tô con, Xe đạp điện'}),
        }

class MonthlyTicketRuleForm(forms.ModelForm):
    class Meta:
        model = MonthlyTicketRules
        fields = ['VehicleTypeID', 'PricePerMonth']
        labels = {
            'VehicleTypeID': 'Loại Xe Áp Dụng',
            'PricePerMonth': 'Giá Vé Tháng (VND)',
        }
        widgets = {
            # Thêm 'class':'input' vào đây
            'PricePerMonth': forms.NumberInput(attrs={'class': 'input', 'placeholder': 'Ví dụ: 100000'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Hiển thị tên loại xe thay vì chỉ ID
        if 'VehicleTypeID' in self.fields: # Kiểm tra xem trường có tồn tại không
            self.fields['VehicleTypeID'].label_from_instance = lambda obj: obj.TypeName


class PerTurnTicketRuleForm(forms.ModelForm):
    class Meta:
        model = PerTurnTicketRules
        # Trong CSDL v4, chúng ta đã bỏ Description khỏi PerTurnTicketRules
        fields = ['VehicleTypeID', 'Price', 'ShiftName', 'TimeFrom', 'TimeTo']
        labels = {
            'VehicleTypeID': 'Loại Xe Áp Dụng',
            'Price': 'Giá Vé Lượt (VND)',
            'ShiftName': 'Tên Ca (Ví dụ: Ca Sáng, Ca Chiều)',
            'TimeFrom': 'Giờ Bắt Đầu Ca (HH:MM:SS)',
            'TimeTo': 'Giờ Kết Thúc Ca (HH:MM:SS)',
        }
        widgets = {
            'Price': forms.NumberInput(attrs={'class': 'input', 'placeholder': 'Ví dụ: 5000'}),
            'ShiftName': forms.TextInput(
                attrs={'class': 'input', 'placeholder': 'Để trống nếu là giá cố định không theo ca'}),
            'TimeFrom': forms.TimeInput(attrs={'class': 'input', 'type': 'time', 'placeholder': 'HH:MM'}),
            'TimeTo': forms.TimeInput(attrs={'class': 'input', 'type': 'time', 'placeholder': 'HH:MM'}),
        }
        help_texts = {
            'ShiftName': 'Nếu không nhập Tên Ca, Giờ Bắt Đầu và Giờ Kết Thúc, quy tắc này có thể được coi là giá cố định cho cả ngày (cần logic xử lý riêng trong view nếu muốn).',
            'TimeFrom': 'Để trống nếu không áp dụng theo giờ cụ thể.',
            'TimeTo': 'Để trống nếu không áp dụng theo giờ cụ thể.',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'VehicleTypeID' in self.fields:
            self.fields['VehicleTypeID'].label_from_instance = lambda obj: obj.TypeName

    def clean(self):
        cleaned_data = super().clean()
        time_from = cleaned_data.get("TimeFrom")
        time_to = cleaned_data.get("TimeTo")
        shift_name = cleaned_data.get("ShiftName")

        # Nếu có TimeFrom thì phải có TimeTo và ngược lại (cho một ca cụ thể)
        if (time_from and not time_to) or (not time_from and time_to):
            self.add_error('TimeFrom', "Cả Giờ Bắt Đầu và Giờ Kết Thúc phải được cung cấp nếu định nghĩa ca theo giờ.")
            self.add_error('TimeTo', "Cả Giờ Bắt Đầu và Giờ Kết Thúc phải được cung cấp nếu định nghĩa ca theo giờ.")

        # Nếu có TimeFrom và TimeTo, thì ShiftName cũng nên có (hoặc tự động tạo)
        if time_from and time_to and not shift_name:
            self.add_error('ShiftName', "Vui lòng nhập Tên Ca nếu bạn định nghĩa Giờ Bắt Đầu và Giờ Kết Thúc.")

        # Logic này cho phép ca không qua đêm. Nếu bạn muốn ca qua đêm (ví dụ 22:00 - 05:00)
        # bạn cần bỏ qua kiểm tra này hoặc xử lý nó phức tạp hơn.
        # Hiện tại, chúng ta giả định các ca đều trong cùng một ngày (TimeFrom < TimeTo).
        if time_from and time_to and time_from >= time_to:
            self.add_error('TimeTo', "Giờ Kết Thúc Ca phải sau Giờ Bắt Đầu Ca (cho ca trong ngày).")

        return cleaned_data

class DateSelectionForm(forms.Form):
    selected_date = forms.DateField(
        label='Chọn ngày xem thống kê',
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=True
    )

class MonthYearSelectionForm(forms.Form):
    # Tạo danh sách các tháng
    MONTH_CHOICES = [(str(i), datetime(2000, i, 1).strftime('%B')) for i in range(1, 13)]
    # Tạo danh sách các năm (ví dụ từ 5 năm trước đến năm hiện tại + 1)
    current_year = datetime.now().year
    YEAR_CHOICES = [(str(i), str(i)) for i in range(current_year - 5, current_year + 2)]

    selected_month = forms.ChoiceField(
        label='Chọn tháng',
        choices=MONTH_CHOICES,
        initial=str(datetime.now().month) # Tháng hiện tại làm mặc định
    )
    selected_year = forms.ChoiceField(
        label='Chọn năm',
        choices=YEAR_CHOICES,
        initial=str(current_year) # Năm hiện tại làm mặc định
    )