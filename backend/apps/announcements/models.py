from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import BaseModel


class Announcement(BaseModel):
    class Kind(models.TextChoices):
        GENERAL = "GENERAL", "Genel duyuru"
        SYSTEM = "SYSTEM", "Sistem duyurusu"

    class SystemKey(models.TextChoices):
        DUTY_NEXT_MONTH_MISSING = "DUTY_NEXT_MONTH_MISSING", "Gelecek ay nöbet bilgisi eksik"
        DUTY_CURRENT_MONTH_MISSING = "DUTY_CURRENT_MONTH_MISSING", "Bu ay nöbet bilgisi eksik"

    class Severity(models.TextChoices):
        INFO = "INFO", "Bilgilendirme"
        WARNING = "WARNING", "Uyarı"
        ACTION_REQUIRED = "ACTION_REQUIRED", "İşlem gerekli"

    class Recurrence(models.TextChoices):
        ONCE = "ONCE", "Tek seferlik"
        DAILY = "DAILY", "Günlük"
        WEEKLY = "WEEKLY", "Haftalık"
        MONTHLY = "MONTHLY", "Aylık"

    class MonthlyMode(models.TextChoices):
        SPECIFIC_DAY = "SPECIFIC_DAY", "Ayın belirli günü"
        DAY_RANGE = "DAY_RANGE", "Ayın belirli gün aralığı"
        FIRST_N_DAYS = "FIRST_N_DAYS", "Ayın ilk N günü"
        LAST_N_DAYS = "LAST_N_DAYS", "Ayın son N günü"
        LAST_WEEK = "LAST_WEEK", "Ayın son haftası"

    class TargetScope(models.TextChoices):
        ALL = "ALL", "Tüm eczaneler"
        PROVINCE = "PROVINCE", "İl"
        DISTRICT = "DISTRICT", "İlçe"
        PHARMACY = "PHARMACY", "Eczane"

    kind = models.CharField(max_length=12, choices=Kind.choices, default=Kind.GENERAL, db_index=True)
    system_key = models.CharField(
        max_length=64, choices=SystemKey.choices, unique=True, null=True, blank=True, editable=False
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    action_label = models.CharField(max_length=80, blank=True, default="")
    severity = models.CharField(max_length=24, choices=Severity.choices, default=Severity.INFO)
    active = models.BooleanField(default=True, db_index=True)

    recurrence = models.CharField(max_length=16, choices=Recurrence.choices, default=Recurrence.ONCE)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    weekdays = models.JSONField(default=list, blank=True, help_text="Pazartesi=0 ... Pazar=6")
    monthly_mode = models.CharField(max_length=24, choices=MonthlyMode.choices, blank=True, default="")
    monthly_day_start = models.PositiveSmallIntegerField(null=True, blank=True)
    monthly_day_end = models.PositiveSmallIntegerField(null=True, blank=True)
    monthly_day_count = models.PositiveSmallIntegerField(null=True, blank=True)

    target_scope = models.CharField(max_length=16, choices=TargetScope.choices, default=TargetScope.ALL)
    target_province = models.ForeignKey(
        "lookups.Il", null=True, blank=True, on_delete=models.PROTECT, related_name="announcements"
    )
    target_district = models.ForeignKey(
        "lookups.Ilce", null=True, blank=True, on_delete=models.PROTECT, related_name="announcements"
    )
    target_pharmacy = models.ForeignKey(
        "pharmacies.Eczane", null=True, blank=True, on_delete=models.PROTECT, related_name="announcements"
    )

    class Meta:
        db_table = "announcements"
        ordering = ("-olusturulma_tarihi",)

    def clean(self):
        errors = {}
        if self.kind == self.Kind.SYSTEM:
            if not self.system_key:
                errors["system_key"] = "Sistem duyurusunda system_key zorunludur."
        elif self.system_key:
            errors["system_key"] = "Genel duyuruda system_key bulunamaz."

        if self.kind == self.Kind.GENERAL:
            if not self.start_date:
                errors["start_date"] = "Başlangıç tarihi zorunludur."
            if self.end_date and self.start_date and self.end_date < self.start_date:
                errors["end_date"] = "Bitiş tarihi başlangıçtan önce olamaz."
            if self.recurrence == self.Recurrence.WEEKLY:
                if not self.weekdays or any(not isinstance(day, int) or day < 0 or day > 6 for day in self.weekdays):
                    errors["weekdays"] = "Haftalık tekrar için 0-6 arası en az bir gün seçilmelidir."
            if self.recurrence == self.Recurrence.MONTHLY:
                if not self.monthly_mode:
                    errors["monthly_mode"] = "Aylık tekrar seçeneği zorunludur."
                if self.monthly_mode in (self.MonthlyMode.SPECIFIC_DAY, self.MonthlyMode.DAY_RANGE):
                    if not self.monthly_day_start or not 1 <= self.monthly_day_start <= 31:
                        errors["monthly_day_start"] = "Ay günü 1-31 arasında olmalıdır."
                if self.monthly_mode == self.MonthlyMode.DAY_RANGE:
                    if not self.monthly_day_end or not 1 <= self.monthly_day_end <= 31:
                        errors["monthly_day_end"] = "Bitiş günü 1-31 arasında olmalıdır."
                    elif self.monthly_day_start and self.monthly_day_end < self.monthly_day_start:
                        errors["monthly_day_end"] = "Gün aralığı başlangıçtan önce bitemez."
                if self.monthly_mode in (self.MonthlyMode.FIRST_N_DAYS, self.MonthlyMode.LAST_N_DAYS):
                    if not self.monthly_day_count or not 1 <= self.monthly_day_count <= 31:
                        errors["monthly_day_count"] = "Gün sayısı 1-31 arasında olmalıdır."

            selected_targets = {
                self.TargetScope.ALL: not any((self.target_province_id, self.target_district_id, self.target_pharmacy_id)),
                self.TargetScope.PROVINCE: bool(self.target_province_id) and not any((self.target_district_id, self.target_pharmacy_id)),
                self.TargetScope.DISTRICT: bool(self.target_district_id) and not any((self.target_province_id, self.target_pharmacy_id)),
                self.TargetScope.PHARMACY: bool(self.target_pharmacy_id) and not any((self.target_province_id, self.target_district_id)),
            }
            if not selected_targets.get(self.target_scope, False):
                errors["target_scope"] = "Hedef kapsamı ile yalnızca ilgili hedef alanı doldurulmalıdır."
        if errors:
            raise ValidationError(errors)


class AnnouncementRead(models.Model):
    announcement = models.ForeignKey(Announcement, on_delete=models.CASCADE, related_name="reads")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="announcement_reads")
    occurrence_date = models.DateField()
    read_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "announcement_reads"
        constraints = [
            models.UniqueConstraint(
                fields=("announcement", "user", "occurrence_date"), name="uniq_announcement_user_occurrence"
            )
        ]


class PharmacyDutyMonth(models.Model):
    pharmacy = models.ForeignKey("pharmacies.Eczane", on_delete=models.CASCADE, related_name="duty_months")
    month = models.DateField(help_text="Ayın ilk günü")
    has_no_duty = models.BooleanField(default=False)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "pharmacy_duty_months"
        constraints = [
            models.UniqueConstraint(fields=("pharmacy", "month"), name="uniq_pharmacy_duty_month")
        ]


class PharmacyDutyDay(models.Model):
    duty_month = models.ForeignKey(PharmacyDutyMonth, on_delete=models.CASCADE, related_name="days")
    date = models.DateField()

    class Meta:
        db_table = "pharmacy_duty_days"
        ordering = ("date",)
        constraints = [
            models.UniqueConstraint(fields=("duty_month", "date"), name="uniq_duty_month_date")
        ]
