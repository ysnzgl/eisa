from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.core.uow import UnitOfWork

from .models import Announcement


class AdminAnnouncementSerializer(serializers.ModelSerializer):
    target_label = serializers.SerializerMethodField()

    class Meta:
        model = Announcement
        fields = (
            "id", "kind", "system_key", "title", "message", "action_label", "severity", "active",
            "recurrence", "start_date", "end_date", "weekdays", "monthly_mode", "monthly_day_start",
            "monthly_day_end", "monthly_day_count", "target_scope", "target_province", "target_district",
            "target_pharmacy", "target_label", "olusturulma_tarihi", "guncellenme_tarihi", "surum",
        )
        read_only_fields = ("id", "kind", "system_key", "target_label", "olusturulma_tarihi", "guncellenme_tarihi", "surum")

    def get_target_label(self, obj):
        target = obj.target_province or obj.target_district or obj.target_pharmacy
        return str(target) if target else "Tüm eczaneler"

    def validate(self, attrs):
        instance = self.instance
        if instance and instance.kind == Announcement.Kind.SYSTEM:
            allowed = {"title", "message", "action_label", "severity", "active"}
            forbidden = set(self.initial_data) - allowed
            if forbidden:
                raise serializers.ValidationError(
                    {key: "Sistem duyurusunda bu alan değiştirilemez." for key in sorted(forbidden)}
                )
        candidate = instance or Announcement(kind=Announcement.Kind.GENERAL)
        for key, value in attrs.items():
            setattr(candidate, key, value)
        if not instance:
            candidate.kind = Announcement.Kind.GENERAL
            candidate.system_key = None
        try:
            candidate.clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict) from exc
        return attrs

    def create(self, validated_data):
        validated_data.update(kind=Announcement.Kind.GENERAL, system_key=None)
        instance = Announcement(**validated_data)
        with UnitOfWork(user=self.context["request"].user) as uow:
            uow.add(instance)
        return instance

    def update(self, instance, validated_data):
        for key, value in validated_data.items():
            setattr(instance, key, value)
        with UnitOfWork(user=self.context["request"].user) as uow:
            uow.update(instance)
        return instance


class AnnouncementDisplaySerializer(serializers.ModelSerializer):
    occurrence_date = serializers.DateField(read_only=True)
    is_read = serializers.BooleanField(read_only=True)
    action_url = serializers.CharField(read_only=True, allow_blank=True)
    target_month = serializers.CharField(read_only=True, allow_blank=True)

    class Meta:
        model = Announcement
        fields = ("id", "kind", "system_key", "title", "message", "action_label", "severity",
                  "occurrence_date", "is_read", "action_url", "target_month")
