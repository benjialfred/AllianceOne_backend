from django.urls import path
from .views import ActiveCVView, TrackEventView, FounderAnalyticsView

urlpatterns = [
    path('cv/active/', ActiveCVView.as_view(), name='founder-cv-active'),
    path('events/', TrackEventView.as_view(), name='founder-track-event'),
    path('analytics/', FounderAnalyticsView.as_view(), name='founder-analytics'),
]
