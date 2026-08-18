from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import ActiveAnnouncementsView, AdminAnnouncementViewSet, AdminDutyCalendarView, DutyCalendarView, MarkAnnouncementReadView

router = DefaultRouter()
router.register("admin", AdminAnnouncementViewSet, basename="admin-announcement")

urlpatterns = [
    path("me/active/", ActiveAnnouncementsView.as_view(), name="active-announcements"),
    path("<int:pk>/read/", MarkAnnouncementReadView.as_view(), name="announcement-read"),
    path("duty/", DutyCalendarView.as_view(), name="duty-calendar"),
    path("admin/duty/", AdminDutyCalendarView.as_view(), name="admin-duty-calendar"),
] + router.urls
