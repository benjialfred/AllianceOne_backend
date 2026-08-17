from decimal import Decimal
from django.db.models import Sum, Count, F, Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import (
    Product, ProductStock, Warehouse, Supplier,
    PurchaseOrder, StockMovement, Category
)
from .serializers import StockMovementSerializer


class InventoryDashboardKPIView(APIView):
    """
    Retourne les KPIs et indicateurs logistiques consolidés en temps réel.
    """
    def get(self, request):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'error': 'X-Tenant-ID requis'}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Total Products & Stocks
        products = Product.objects.filter(organization=tenant, is_active=True).prefetch_related('stocks')
        total_products_count = products.count()

        out_of_stock_count = 0
        low_stock_count = 0
        in_stock_count = 0
        total_stock_units = Decimal('0.00')
        total_valuation_pmp = Decimal('0.00')

        for prod in products:
            qty_hand = prod.total_stock_on_hand
            total_stock_units += qty_hand
            total_valuation_pmp += prod.total_valuation

            if qty_hand <= Decimal('0.00'):
                out_of_stock_count += 1
            elif qty_hand <= prod.min_stock_level:
                low_stock_count += 1
            else:
                in_stock_count += 1

        # 2. Warehouses summary
        warehouses = Warehouse.objects.filter(organization=tenant, is_active=True).annotate(
            stocks_count=Count('stocks')
        )
        total_warehouses_count = warehouses.count()

        # 3. Pending Purchase Orders
        pending_orders = PurchaseOrder.objects.filter(
            organization=tenant,
            status__in=['COMMANDE', 'RECEPTION_PARTIELLE']
        )
        pending_orders_count = pending_orders.count()
        inbound_expected_value = pending_orders.aggregate(total=Sum('total_ttc'))['total'] or Decimal('0.00')

        # 4. Valuation by Category
        categories = Category.objects.filter(organization=tenant).prefetch_related('products', 'products__stocks')
        category_breakdown = []
        for cat in categories:
            cat_val = sum(p.total_valuation for p in cat.products.all())
            cat_qty = sum(p.total_stock_on_hand for p in cat.products.all())
            category_breakdown.append({
                'id': str(cat.id),
                'name': cat.name,
                'code': cat.code,
                'items_count': cat.products.count(),
                'total_quantity': float(cat_qty),
                'total_valuation': float(cat_val)
            })

        # Sort categories by valuation descending
        category_breakdown.sort(key=lambda x: x['total_valuation'], reverse=True)

        # 5. Stock breakdown by warehouse
        warehouse_breakdown = []
        for wh in warehouses:
            wh_stocks = ProductStock.objects.filter(organization=tenant, warehouse=wh)
            wh_qty = sum(s.quantity_on_hand for s in wh_stocks)
            wh_val = sum(s.total_value for s in wh_stocks)
            warehouse_breakdown.append({
                'id': str(wh.id),
                'code': wh.code,
                'name': wh.name,
                'total_quantity': float(wh_qty),
                'total_valuation': float(wh_val)
            })

        return Response({
            'kpis': {
                'total_valuation_pmp': float(total_valuation_pmp),
                'total_stock_units': float(total_stock_units),
                'total_products_count': total_products_count,
                'out_of_stock_count': out_of_stock_count,
                'low_stock_count': low_stock_count,
                'in_stock_count': in_stock_count,
                'total_warehouses_count': total_warehouses_count,
                'pending_orders_count': pending_orders_count,
                'inbound_expected_value': float(inbound_expected_value)
            },
            'category_breakdown': category_breakdown,
            'warehouse_breakdown': warehouse_breakdown
        })


class InventoryDashboardIntelligenceView(APIView):
    """
    Génère des suggestions intelligentes de réapprovisionnement et alertes d'anomalies.
    """
    def get(self, request):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'error': 'X-Tenant-ID requis'}, status=status.HTTP_400_BAD_REQUEST)

        alerts = []
        products = Product.objects.filter(organization=tenant, is_active=True).select_related('unit', 'category').prefetch_related('stocks')

        for prod in products:
            qty_hand = prod.total_stock_on_hand
            if qty_hand <= Decimal('0.00'):
                alerts.append({
                    'id': f"rupture-{prod.id}",
                    'severity': 'critical',
                    'type': 'OUT_OF_STOCK',
                    'title': f"Rupture totale : {prod.name}",
                    'message': f"Le stock est à zéro ({qty_hand} {prod.unit.symbol if prod.unit else 'u'}). Seuil d'alerte configuré à {prod.min_stock_level}.",
                    'action_label': "Commander",
                    'suggested_reorder_qty': float(prod.reorder_quantity or (prod.min_stock_level * 2)),
                    'product_id': str(prod.id),
                    'sku': prod.sku,
                    'category': prod.category.name if prod.category else 'Général'
                })
            elif qty_hand <= prod.min_stock_level:
                alerts.append({
                    'id': f"alerte-{prod.id}",
                    'severity': 'warning',
                    'type': 'LOW_STOCK',
                    'title': f"Stock critique : {prod.name}",
                    'message': f"Stock restant: {qty_hand} {prod.unit.symbol if prod.unit else 'u'} (seuil: {prod.min_stock_level}). Réapprovisionnement suggéré : {prod.reorder_quantity}.",
                    'action_label': "Réapprovisionner",
                    'suggested_reorder_qty': float(prod.reorder_quantity),
                    'product_id': str(prod.id),
                    'sku': prod.sku,
                    'category': prod.category.name if prod.category else 'Général'
                })

        # Overdue purchase orders
        from datetime import date
        today = date.today()
        late_orders = PurchaseOrder.objects.filter(
            organization=tenant,
            status='COMMANDE',
            expected_delivery_date__lt=today
        ).select_related('supplier')

        for order in late_orders:
            alerts.append({
                'id': f"retard-{order.id}",
                'severity': 'info',
                'type': 'LATE_DELIVERY',
                'title': f"Livraison en retard : {order.order_number}",
                'message': f"Commande fournisseur {order.supplier.name} attendue le {order.expected_delivery_date}. Relance suggérée.",
                'action_label': "Voir Commande",
                'order_id': str(order.id)
            })

        return Response({'alerts': alerts, 'count': len(alerts)})


class InventoryDashboardTimelineView(APIView):
    """
    Flux d'activité logistique récent.
    """
    def get(self, request):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'error': 'X-Tenant-ID requis'}, status=status.HTTP_400_BAD_REQUEST)

        movements = StockMovement.objects.filter(organization=tenant).select_related(
            'product', 'product__unit', 'source_warehouse', 'target_warehouse', 'performed_by'
        ).order_by('-created_at')[:20]

        serializer = StockMovementSerializer(movements, many=True)
        return Response({'timeline': serializer.data})
