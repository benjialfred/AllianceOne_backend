from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Count, Q
from .models import FounderCV, FounderActivityEvent
from .permissions import IsFounderOrAdmin

class ActiveCVView(APIView):
    """
    Récupérer le CV actif du fondateur.
    """
    permission_classes = [] # Public access

    def get(self, request):
        active_cv = FounderCV.objects.filter(is_active=True).first()
        if not active_cv:
            return Response({"detail": "No active CV found"}, status=status.HTTP_404_NOT_FOUND)
        
        return Response({
            "title": active_cv.title,
            "version": active_cv.version,
            "file_url": request.build_absolute_uri(active_cv.file.url) if active_cv.file else None,
            "updated_at": active_cv.updated_at
        })


class TrackEventView(APIView):
    """
    Enregistrer une interaction avec le profil du fondateur.
    """
    permission_classes = [] # Public access (but tracks user if authenticated)

    def post(self, request):
        event_type = request.data.get('event_type')
        if not event_type or event_type not in dict(FounderActivityEvent.EVENT_TYPES).keys():
            return Response({"detail": "Invalid event_type"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check tenant context if available (from headers/middleware usually, but here we can extract if provided)
        organization = request.tenant if hasattr(request, 'tenant') else None
        
        session_id = request.data.get('session_id')
        user = request.user if request.user.is_authenticated else None
        
        # Avoid duplicate tracking for the same session/user within a short timeframe if needed
        # But for simplicity, we just log it.
        
        FounderActivityEvent.objects.create(
            user=user,
            organization=organization,
            event_type=event_type,
            session_id=session_id,
            metadata=request.data.get('metadata', {})
        )
        
        return Response({"status": "tracked"}, status=status.HTTP_201_CREATED)


class FounderAnalyticsView(APIView):
    """
    Vue réservée au fondateur pour voir les statistiques d'interaction.
    """
    permission_classes = [IsFounderOrAdmin]

    def get(self, request):
        # Overview stats
        total_profile_views = FounderActivityEvent.objects.filter(event_type='PROFILE_VIEW').count()
        total_cv_views = FounderActivityEvent.objects.filter(event_type='CV_VIEW').count()
        total_downloads = FounderActivityEvent.objects.filter(event_type='CV_DOWNLOAD').count()
        
        # Calculate conversion rate (Profile View -> CV View)
        # For a true funnel, we should count unique sessions/users
        unique_profile_visitors = FounderActivityEvent.objects.filter(event_type='PROFILE_VIEW').values('user', 'session_id').distinct().count()
        unique_cv_viewers = FounderActivityEvent.objects.filter(event_type='CV_VIEW').values('user', 'session_id').distinct().count()
        
        conversion_rate = 0
        if unique_profile_visitors > 0:
            conversion_rate = (unique_cv_viewers / unique_profile_visitors) * 100
            
        recent_activity = FounderActivityEvent.objects.order_by('-created_at')[:20]
        recent_activity_data = []
        for event in recent_activity:
            recent_activity_data.append({
                "id": str(event.id),
                "event_type": event.event_type,
                "user": event.user.email if event.user else "Anonymous",
                "organization": event.organization.name if event.organization else "N/A",
                "timestamp": event.created_at,
            })
            
        return Response({
            "overview": {
                "profile_views": total_profile_views,
                "unique_visitors": unique_profile_visitors,
                "cv_views": total_cv_views,
                "unique_cv_viewers": unique_cv_viewers,
                "downloads": total_downloads,
                "conversion_rate": round(conversion_rate, 2)
            },
            "recent_activity": recent_activity_data
        })
