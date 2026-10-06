from rest_framework import viewsets, views, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.core.cache import cache
from decimal import Decimal
from .services import IzyBoostService, IzyBoostAPIError
from .models import BoostOrder, BoostOrderStatus
from .serializers import BoostOrderSerializer, CreateBoostOrderSerializer

# Constantes de tarification
USD_TO_XAF = Decimal('650.0')
PROFIT_MARGIN_MULTIPLIER = Decimal('2.0') # 100% markup

def calculate_price_xaf(rate_usd_per_1000: str, quantity: int) -> Decimal:
    """Calcule le prix de vente en XAF basé sur le tarif IzyBoost (USD par 1000)"""
    rate = Decimal(str(rate_usd_per_1000))
    cost_usd = (rate / Decimal('1000')) * Decimal(str(quantity))
    selling_price_xaf = cost_usd * USD_TO_XAF * PROFIT_MARGIN_MULTIPLIER
    # Arrondir à la dizaine supérieure pour faire propre (ex: 153 XAF -> 160 XAF)
    return Decimal(round(selling_price_xaf / 10) * 10)

class BoostServicesView(views.APIView):
    """
    Liste les services IzyBoost disponibles avec les tarifs convertis et margés.
    """
    permission_classes = [] # AllowAny

    def get(self, request):
        # On utilise le cache pour ne pas spammer l'API IzyBoost à chaque chargement de page
        cached_services = cache.get('izyboost_services')
        if cached_services:
            return Response(cached_services)

        izy_service = IzyBoostService()
        try:
            raw_services = izy_service.get_services()
            
            # Formater et ajouter notre propre tarif
            formatted_services = []
            for s in raw_services:
                # On ne garde que les services valides
                if 'rate' in s:
                    # Calcul du prix de vente pour 1000 unités en XAF
                    selling_rate_xaf = calculate_price_xaf(s['rate'], 1000)
                    s['selling_rate_xaf'] = str(selling_rate_xaf)
                    formatted_services.append(s)

            # Mettre en cache pour 1 heure (3600 secondes)
            cache.set('izyboost_services', formatted_services, 3600)
            return Response(formatted_services)
        except IzyBoostAPIError as e:
            return Response({"error": str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

class BoostOrderViewSet(viewsets.ModelViewSet):
    """
    Gère les commandes de boost de l'utilisateur.
    """
    serializer_class = BoostOrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return BoostOrder.objects.filter(user=self.request.user).order_by('-created_at')

    def create(self, request, *args, **kwargs):
        serializer = CreateBoostOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        service_id = data['service_id']
        quantity = data['quantity']
        
        # 1. Vérifier le service et calculer le prix exact
        cached_services = cache.get('izyboost_services')
        izy_service_client = IzyBoostService()
        
        if not cached_services:
            try:
                cached_services = izy_service_client.get_services()
            except IzyBoostAPIError as e:
                return Response({"error": "Service indisponible"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
                
        service_info = next((s for s in cached_services if s['service'] == service_id), None)
        if not service_info:
            return Response({"error": "Service invalide"}, status=status.HTTP_400_BAD_REQUEST)
            
        # Vérification des limites
        if quantity < int(service_info['min']) or quantity > int(service_info['max']):
            return Response({"error": f"La quantité doit être entre {service_info['min']} et {service_info['max']}"}, status=status.HTTP_400_BAD_REQUEST)

        # Calcul des prix
        rate_usd = Decimal(str(service_info['rate']))
        cost_usd = (rate_usd / Decimal('1000')) * Decimal(str(quantity))
        selling_price_xaf = calculate_price_xaf(service_info['rate'], quantity)

        # 2. Créer la commande locale (Statut PENDING)
        organization = getattr(request, 'tenant', None) or getattr(request, 'organization', None)
        if not organization and hasattr(request.user, 'organizations') and request.user.organizations.exists():
             organization = request.user.organizations.first()

        order = BoostOrder.objects.create(
            organization=organization,
            user=request.user,
            service_id=service_id,
            service_name=service_info['name'],
            target_link=data['target_link'],
            quantity=quantity,
            comments=data.get('comments', ''),
            cost_price_usd=cost_usd,
            selling_price=selling_price_xaf,
            currency='XAF',
            status=BoostOrderStatus.PROCESSING # On le passe en PROCESSING directement pour l'instant (Paiement direct depuis le solde SMM)
        )

        # 3. TODO: Ici, intégrer le paiement via Nelsius ou débiter le Wallet local du client
        # Pour le moment, on lance la commande directement sur IzyBoost pour la démo
        
        try:
            remote_response = izy_service_client.create_order(
                service_id=service_id,
                link=data['target_link'],
                quantity=quantity,
                comments=data.get('comments')
            )
            
            if 'order' in remote_response:
                order.remote_order_id = str(remote_response['order'])
                order.save()
            else:
                order.status = BoostOrderStatus.FAILED
                order.save()
                return Response({"error": "Erreur inattendue de l'API partenaire"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except IzyBoostAPIError as e:
            order.status = BoostOrderStatus.CANCELED
            order.save()
            return Response({"error": f"Erreur partenaire: {str(e)}"}, status=status.HTTP_502_BAD_GATEWAY)

        return Response(BoostOrderSerializer(order).data, status=status.HTTP_201_CREATED)
