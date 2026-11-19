from django.urls import path
from config.views import health
from accounts.views import RegisterView, LoginView, MeView, LogoutView
from farms.views import FarmCollectionView, FarmUpdateView, PlotCreateView, PlotUpdateView
from operations.views import OperationCalendarView, OperationCollectionView, OperationCreateView, OperationDetailView

urlpatterns = [
    path("api/v1/health", health),
    path("api/v1/auth/register", RegisterView.as_view()),
    path("api/v1/auth/login", LoginView.as_view()),
    path("api/v1/auth/me", MeView.as_view()),
    path("api/v1/auth/logout", LogoutView.as_view()),
    path("api/v1/farms", FarmCollectionView.as_view()),
    path("api/v1/farms/<int:farm_id>", FarmUpdateView.as_view()),
    path("api/v1/farms/<int:farm_id>/plots", PlotCreateView.as_view()),
    path("api/v1/plots/<int:plot_id>", PlotUpdateView.as_view()),
    path("api/v1/operations", OperationCreateView.as_view()),
    path("api/v1/operations/calendar", OperationCalendarView.as_view()),
    path("api/v1/operations/<int:operation_id>", OperationDetailView.as_view()),
]
handler404 = "config.errors.not_found"
