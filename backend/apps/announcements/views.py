from datetime import date

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.uow import UnitOfWork
from apps.pharmacies.permissions import IsEczaci, IsSuperAdmin

from .models import Announcement, AnnouncementRead, PharmacyDutyDay, PharmacyDutyMonth
from .serializers import AdminAnnouncementSerializer, AnnouncementDisplaySerializer
from .services import applies_to_pharmacy, is_general_occurrence, istanbul_today, month_start, system_context


class AdminAnnouncementViewSet(viewsets.ModelViewSet):
    permission_classes = [IsSuperAdmin]
    serializer_class = AdminAnnouncementSerializer
    queryset = Announcement.objects.select_related(
        "target_province", "target_district", "target_pharmacy"
    ).all()
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.kind == Announcement.Kind.SYSTEM:
            return Response(
                {"detail": "Sistem duyuruları silinemez; yalnızca pasifleştirilebilir."},
                status=status.HTTP_405_METHOD_NOT_ALLOWED,
            )
        with UnitOfWork(user=request.user) as uow:
            uow.delete(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ActiveAnnouncementsView(APIView):
    permission_classes = [IsEczaci]

    def get(self, request):
        today = istanbul_today()
        pharmacy = request.user.eczane
        include_read = request.query_params.get("include_read", "false").lower() == "true"
        read_ids = set(AnnouncementRead.objects.filter(
            user=request.user, occurrence_date=today
        ).values_list("announcement_id", flat=True))
        output = []
        announcements = Announcement.objects.filter(active=True).select_related(
            "target_province", "target_district", "target_pharmacy"
        )
        for announcement in announcements:
            context = None
            if announcement.kind == Announcement.Kind.GENERAL:
                if is_general_occurrence(announcement, today) and applies_to_pharmacy(announcement, pharmacy):
                    context = {"action_url": "", "target_month": ""}
            else:
                context = system_context(announcement, pharmacy, today)
            if context is None:
                continue
            is_read = announcement.id in read_ids
            if is_read and not include_read:
                continue
            announcement.occurrence_date = today
            announcement.is_read = is_read
            announcement.action_url = context["action_url"]
            announcement.target_month = context["target_month"]
            output.append(AnnouncementDisplaySerializer(announcement).data)
        return Response(output)


class MarkAnnouncementReadView(APIView):
    permission_classes = [IsEczaci]

    def post(self, request, pk):
        announcement = get_object_or_404(Announcement, pk=pk, active=True)
        today = istanbul_today()
        pharmacy = request.user.eczane
        valid = (
            is_general_occurrence(announcement, today) and applies_to_pharmacy(announcement, pharmacy)
            if announcement.kind == Announcement.Kind.GENERAL
            else system_context(announcement, pharmacy, today) is not None
        )
        if not valid:
            return Response({"detail": "Bu duyurunun bugün için aktif bir occurrence kaydı yok."}, status=400)
        receipt, created = AnnouncementRead.objects.get_or_create(
            announcement=announcement, user=request.user, occurrence_date=today
        )
        return Response(
            {"occurrence_date": receipt.occurrence_date, "read_at": receipt.read_at},
            status=201 if created else 200,
        )


class DutyCalendarView(APIView):
    permission_classes = [IsEczaci]

    @staticmethod
    def parse_month(raw):
        try:
            parsed = date.fromisoformat(f"{raw}-01")
        except (TypeError, ValueError):
            raise serializers.ValidationError({"month": "Ay YYYY-MM biçiminde olmalıdır."})
        return month_start(parsed)

    def get(self, request):
        month = self.parse_month(request.query_params.get("month"))
        duty = PharmacyDutyMonth.objects.filter(
            pharmacy=request.user.eczane, month=month
        ).prefetch_related("days").first()
        return Response({
            "month": month.strftime("%Y-%m"),
            "has_no_duty": duty.has_no_duty if duty else False,
            "dates": [item.date for item in duty.days.all()] if duty else [],
        })

    @transaction.atomic
    def put(self, request):
        month = self.parse_month(request.data.get("month"))
        has_no_duty = request.data.get("has_no_duty", False)
        dates = request.data.get("dates", [])
        if not isinstance(has_no_duty, bool) or not isinstance(dates, list):
            raise serializers.ValidationError("has_no_duty boolean, dates liste olmalıdır.")
        parsed_dates = []
        for raw in dates:
            try:
                parsed = date.fromisoformat(raw)
            except (TypeError, ValueError):
                raise serializers.ValidationError({"dates": f"Geçersiz tarih: {raw}"})
            if month_start(parsed) != month:
                raise serializers.ValidationError({"dates": "Tüm nöbet günleri seçili ay içinde olmalıdır."})
            parsed_dates.append(parsed)
        if has_no_duty and parsed_dates:
            raise serializers.ValidationError("Nöbetim yok seçiliyken nöbet günü girilemez.")

        duty, _ = PharmacyDutyMonth.objects.update_or_create(
            pharmacy=request.user.eczane,
            month=month,
            defaults={"has_no_duty": has_no_duty, "updated_by": request.user},
        )
        duty.days.all().delete()
        PharmacyDutyDay.objects.bulk_create(
            [PharmacyDutyDay(duty_month=duty, date=item) for item in sorted(set(parsed_dates))]
        )
        return Response({
            "month": month.strftime("%Y-%m"),
            "has_no_duty": duty.has_no_duty,
            "dates": sorted(set(parsed_dates)),
        })
