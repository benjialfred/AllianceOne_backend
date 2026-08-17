from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .services import FinanceService


class FinanceDashboardView(APIView):
    """
    Fournit les statistiques consolidées, KPIs temps réel, flux mensuels
    et alertes de trésorerie pour le tableau de bord d'entreprise.
    """
    def get(self, request):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'error': 'Organisation requise.'}, status=status.HTTP_400_BAD_REQUEST)

        currency_filter = request.query_params.get('currency', 'ALL')
        data = FinanceService.get_dashboard_analytics(tenant, currency_filter=currency_filter)
        return Response(data)
