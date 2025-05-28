from django.core.management.base import BaseCommand
from parking_management.models import Vehicle
from django.utils import timezone
# day la cu phap thay the trigger dung de reset ve hang thang
class Command(BaseCommand):
    help = 'Resets the HasMonthlyTicket flag for all vehicles to False at the beginning of the month'

    def handle(self, *args, **options):
        today = timezone.now().date()
        # Chỉ thực hiện nếu là ngày mùng 1 của tháng
        if today.day == 1:
            updated_count = Vehicle.objects.update(HasMonthlyTicket=False)
            self.stdout.write(self.style.SUCCESS(f'Successfully reset HasMonthlyTicket for {updated_count} vehicles.'))
        else:
            self.stdout.write(self.style.NOTICE(f'Today is not the 1st of the month. No action taken. ({today})'))