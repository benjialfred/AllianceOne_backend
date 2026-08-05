from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from platform_services.dashboards.models import DashboardLayout, WidgetPlacement
from platform_services.dashboards.api.serializers import DashboardLayoutSerializer

class DashboardLayoutViewSet(viewsets.ModelViewSet):
    serializer_class = DashboardLayoutSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        # Pour le super admin, on peut filtrer les dashboards platform-level.
        # Sinon, on filtre par organization_id.
        return DashboardLayout.objects.all()

    @action(detail=False, methods=['get'])
    def my_dashboard(self, request):
        """
        Renvoie le layout configuré pour l'utilisateur courant ou l'organisation courante,
        ou le dashboard par défaut du Super Admin.
        """
        # Simplification: on récupère le premier dashboard dispo ou on le crée
        layout = None
        if request.user.is_authenticated:
            layout = DashboardLayout.objects.filter(user=request.user).first()
        if not layout:
            layout = DashboardLayout.objects.filter(is_default=True).first()
            if not layout:
                layout = DashboardLayout.objects.create(name="Default Dashboard", is_default=True)
                
                # Créer quelques widgets par défaut pour tester
                WidgetPlacement.objects.create(layout=layout, widget_id='users_stats', x=0, y=0, w=4, h=2)
                WidgetPlacement.objects.create(layout=layout, widget_id='recent_activities', x=4, y=0, w=4, h=4)
                WidgetPlacement.objects.create(layout=layout, widget_id='orgs_to_certify', x=8, y=0, w=4, h=2)

        serializer = self.get_serializer(layout)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def save_layout(self, request, pk=None):
        """
        Sauvegarde un layout (met à jour les WidgetPlacement).
        Expects: {'widgets': [{'widget_id': '...', 'x': 0, 'y': 0, 'w': 2, 'h': 2}, ...]}
        """
        layout = self.get_object()
        widgets_data = request.data.get('widgets', [])
        
        # On supprime les anciens placements pour ce layout
        WidgetPlacement.objects.filter(layout=layout).delete()
        
        for w_data in widgets_data:
            WidgetPlacement.objects.create(
                layout=layout,
                widget_id=w_data['widget_id'],
                x=w_data['x'],
                y=w_data['y'],
                w=w_data['w'],
                h=w_data['h'],
                config=w_data.get('config', {})
            )
            
        return Response({"status": "layout updated"})
