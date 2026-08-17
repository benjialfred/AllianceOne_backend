from decimal import Decimal
from django.db import transaction
from django.db.models import Q
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from platform_services.identity.mixins import TenantQuerySetMixin

from .models import (
    Category, Unit, Warehouse, WarehouseLocation,
    Product, ProductStock, Supplier, ProductBatch, ProductSupplier, SerialNumber,
    PurchaseOrder, PurchaseOrderItem,
    StockMovement, InventoryAudit, InventoryAuditItem,
    BillOfMaterial, BOMItem, WorkOrder
)
from .serializers import (
    CategorySerializer, UnitSerializer, WarehouseSerializer, WarehouseLocationSerializer,
    ProductSerializer, ProductStockSerializer, SupplierSerializer, ProductBatchSerializer,
    ProductSupplierSerializer, SerialNumberSerializer, PurchaseOrderSerializer, PurchaseOrderItemSerializer,
    StockMovementSerializer, InventoryAuditSerializer, InventoryAuditItemSerializer,
    BillOfMaterialSerializer, WorkOrderSerializer
)
from .services import InventoryService


class CategoryViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    search_fields = ['name', 'code']


class UnitViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = Unit.objects.all()
    serializer_class = UnitSerializer
    search_fields = ['name', 'symbol']


class WarehouseViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = Warehouse.objects.prefetch_related('locations', 'stocks').all()
    serializer_class = WarehouseSerializer
    search_fields = ['name', 'code', 'manager_name', 'city']

    @action(detail=True, methods=['get'])
    def stock_summary(self, request, pk=None):
        warehouse = self.get_object()
        stocks = ProductStock.objects.filter(warehouse=warehouse, organization=request.tenant).select_related('product', 'product__unit', 'location')
        serializer = ProductStockSerializer(stocks, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def transfer_stock(self, request):
        tenant = getattr(request, 'tenant', None)
        product_id = request.data.get('product_id')
        source_wh_id = request.data.get('source_warehouse_id')
        target_wh_id = request.data.get('target_warehouse_id')
        quantity = Decimal(str(request.data.get('quantity', '0')))
        notes = request.data.get('notes', '')

        if not product_id or not source_wh_id or not target_wh_id or quantity <= Decimal('0'):
            return Response({'error': 'Tous les champs (produit, source, destination, quantité > 0) sont requis.'}, status=status.HTTP_400_BAD_REQUEST)

        if source_wh_id == target_wh_id:
            return Response({'error': 'Le dépôt source et le dépôt de destination doivent être différents.'}, status=status.HTTP_400_BAD_REQUEST)

        product = Product.objects.get(id=product_id, organization=tenant)
        source_wh = Warehouse.objects.get(id=source_wh_id, organization=tenant)
        target_wh = Warehouse.objects.get(id=target_wh_id, organization=tenant)

        movement = InventoryService.process_stock_movement(
            tenant=tenant,
            product=product,
            movement_type='TRANSFERT_DEPOT',
            quantity=quantity,
            source_warehouse=source_wh,
            target_warehouse=target_wh,
            reference_document=f"TRF-{source_wh.code}->{target_wh.code}",
            reason=notes or f"Transfert direct de {source_wh.name} vers {target_wh.name}",
            performed_by=request.user if request.user.is_authenticated else None
        )

        return Response(StockMovementSerializer(movement).data, status=status.HTTP_201_CREATED)


class WarehouseLocationViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = WarehouseLocation.objects.all()
    serializer_class = WarehouseLocationSerializer
    filterset_fields = ['warehouse']


class ProductViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = Product.objects.select_related('category', 'unit').prefetch_related('stocks', 'stocks__warehouse').all()
    serializer_class = ProductSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        query = self.request.query_params.get('q', '')
        category_id = self.request.query_params.get('category')
        stock_status_filter = self.request.query_params.get('status')
        warehouse_id = self.request.query_params.get('warehouse')

        if query:
            qs = qs.filter(Q(name__icontains=query) | Q(sku__icontains=query) | Q(barcode__icontains=query))
        
        if category_id:
            qs = qs.filter(category_id=category_id)

        if warehouse_id:
            qs = qs.filter(stocks__warehouse_id=warehouse_id).distinct()

        # Filtering in memory for property statuses if needed, or by annotations
        if stock_status_filter:
            # We can filter in memory or evaluate
            if stock_status_filter == 'OUT_OF_STOCK':
                qs = [p for p in qs if p.stock_status == 'OUT_OF_STOCK']
            elif stock_status_filter == 'LOW_STOCK':
                qs = [p for p in qs if p.stock_status == 'LOW_STOCK']
            elif stock_status_filter == 'IN_STOCK':
                qs = [p for p in qs if p.stock_status == 'IN_STOCK']

        return qs

    @action(detail=True, methods=['get'])
    def batches(self, request, pk=None):
        product = self.get_object()
        tenant = getattr(request, 'tenant', None)
        batches = ProductBatch.objects.filter(organization=tenant, product=product).order_by('expiry_date')
        serializer = ProductBatchSerializer(batches, many=True)
        return Response(serializer.data)

    def perform_create(self, serializer):
        tenant = getattr(self.request, 'tenant', None)
        product = serializer.save(organization=tenant)

        # Initial stock creation if specified in request
        initial_warehouse_id = self.request.data.get('initial_warehouse')
        initial_qty = Decimal(str(self.request.data.get('initial_quantity', '0')))
        
        if initial_warehouse_id and initial_qty > Decimal('0'):
            warehouse = Warehouse.objects.get(id=initial_warehouse_id, organization=tenant)
            InventoryService.process_stock_movement(
                tenant=tenant,
                product=product,
                movement_type='ENTREE_AJUSTEMENT',
                quantity=initial_qty,
                unit_cost=product.purchase_price,
                target_warehouse=warehouse,
                reference_document="STOCK-INITIAL",
                reason="Création de fiche article avec stock initial",
                performed_by=self.request.user if self.request.user.is_authenticated else None
            )

    @action(detail=True, methods=['post'])
    def adjust_stock(self, request, pk=None):
        product = self.get_object()
        tenant = getattr(request, 'tenant', None)
        warehouse_id = request.data.get('warehouse_id')
        new_quantity = Decimal(str(request.data.get('new_quantity', '0')))
        reason = request.data.get('reason', 'Ajustement manuel de stock')

        warehouse = Warehouse.objects.get(id=warehouse_id, organization=tenant)
        stock_obj, _ = ProductStock.objects.get_or_create(
            organization=tenant, product=product, warehouse=warehouse,
            defaults={'pmp_cost': product.purchase_price}
        )

        current_qty = stock_obj.quantity_on_hand
        diff = new_quantity - current_qty

        if diff > Decimal('0'):
            movement = InventoryService.process_stock_movement(
                tenant=tenant,
                product=product,
                movement_type='ENTREE_AJUSTEMENT',
                quantity=diff,
                unit_cost=stock_obj.pmp_cost or product.purchase_price,
                target_warehouse=warehouse,
                reference_document="AJUST-MANUEL",
                reason=reason,
                performed_by=request.user if request.user.is_authenticated else None
            )
        elif diff < Decimal('0'):
            movement = InventoryService.process_stock_movement(
                tenant=tenant,
                product=product,
                movement_type='SORTIE_AJUSTEMENT',
                quantity=abs(diff),
                unit_cost=stock_obj.pmp_cost or product.purchase_price,
                source_warehouse=warehouse,
                reference_document="AJUST-MANUEL",
                reason=reason,
                performed_by=request.user if request.user.is_authenticated else None
            )
        else:
            return Response({'message': 'Aucun changement de quantité détecté.'})

        return Response(StockMovementSerializer(movement).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def reserve(self, request, pk=None):
        product = self.get_object()
        tenant = getattr(request, 'tenant', None)
        warehouse_id = request.data.get('warehouse_id')
        quantity = Decimal(str(request.data.get('quantity', '0')))

        if not warehouse_id or quantity <= Decimal('0'):
            return Response({'error': 'L\'entrepôt et une quantité > 0 sont requis.'}, status=status.HTTP_400_BAD_REQUEST)

        warehouse = Warehouse.objects.get(id=warehouse_id, organization=tenant)
        try:
            stock = InventoryService.reserve_stock(tenant, product, warehouse, quantity)
            return Response(ProductStockSerializer(stock).data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def release_reservation(self, request, pk=None):
        product = self.get_object()
        tenant = getattr(request, 'tenant', None)
        warehouse_id = request.data.get('warehouse_id')
        quantity = Decimal(str(request.data.get('quantity', '0')))

        if not warehouse_id or quantity <= Decimal('0'):
            return Response({'error': 'L\'entrepôt et une quantité > 0 sont requis.'}, status=status.HTTP_400_BAD_REQUEST)

        warehouse = Warehouse.objects.get(id=warehouse_id, organization=tenant)
        try:
            stock = InventoryService.release_reservation(tenant, product, warehouse, quantity)
            return Response(ProductStockSerializer(stock).data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def movements(self, request, pk=None):
        product = self.get_object()
        tenant = getattr(request, 'tenant', None)
        movements = StockMovement.objects.filter(product=product, organization=tenant).select_related(
            'source_warehouse', 'target_warehouse', 'performed_by'
        ).order_by('-created_at')[:50]
        serializer = StockMovementSerializer(movements, many=True)
        return Response(serializer.data)


class ProductBatchViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = ProductBatch.objects.select_related('product').all()
    serializer_class = ProductBatchSerializer
    search_fields = ['batch_number', 'product__name', 'product__sku']
    filterset_fields = ['product']

    def get_queryset(self):
        qs = super().get_queryset()
        status_filter = self.request.query_params.get('status')
        if status_filter == 'expired':
            from django.utils import timezone
            qs = qs.filter(expiry_date__lt=timezone.now().date())
        elif status_filter == 'expiring_soon':
            from django.utils import timezone
            import datetime
            thirty_days_later = timezone.now().date() + datetime.timedelta(days=30)
            qs = qs.filter(expiry_date__gte=timezone.now().date(), expiry_date__lte=thirty_days_later)
        return qs


class SerialNumberViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = SerialNumber.objects.select_related('product', 'batch', 'warehouse').all()
    serializer_class = SerialNumberSerializer
    search_fields = ['serial_number', 'product__name', 'product__sku', 'batch__batch_number']
    filterset_fields = ['product', 'batch', 'warehouse', 'status']

    def perform_create(self, serializer):
        tenant = getattr(self.request, 'tenant', None)
        serializer.save(organization=tenant)


class SupplierViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = Supplier.objects.prefetch_related('purchase_orders').all()
    serializer_class = SupplierSerializer
    search_fields = ['name', 'code', 'contact_name', 'email', 'phone']


class ProductSupplierViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = ProductSupplier.objects.select_related('product', 'supplier').all()
    serializer_class = ProductSupplierSerializer
    search_fields = ['supplier_product_code', 'product__name', 'supplier__name']
    filterset_fields = ['product', 'supplier']

    def perform_create(self, serializer):
        tenant = getattr(self.request, 'tenant', None)
        serializer.save(organization=tenant)


class PurchaseOrderViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = PurchaseOrder.objects.select_related('supplier', 'warehouse').prefetch_related('items', 'items__product').all()
    serializer_class = PurchaseOrderSerializer
    search_fields = ['order_number', 'supplier__name']
    filterset_fields = ['status', 'supplier', 'warehouse']

    @action(detail=False, methods=['post'], url_path='auto-replenish')
    def auto_replenish(self, request):
        from .tasks import generate_auto_replenishment_orders
        tenant = getattr(request, 'tenant', None)
        count = generate_auto_replenishment_orders(tenant)
        return Response({'message': f'{count} commande(s) générée(s) avec succès.'})

    def perform_create(self, serializer):
        tenant = getattr(self.request, 'tenant', None)
        items_data = self.request.data.get('items', [])
        
        with transaction.atomic():
            order = serializer.save(organization=tenant, created_by=self.request.user if self.request.user.is_authenticated else None)
            total_ht = Decimal('0.00')
            total_tax = Decimal('0.00')

            for item_info in items_data:
                product = Product.objects.get(id=item_info['product'], organization=tenant)
                ordered_qty = Decimal(str(item_info['ordered_quantity']))
                unit_price = Decimal(str(item_info.get('unit_price', product.purchase_price)))
                tax_rate = Decimal(str(item_info.get('tax_rate', '19.25')))
                line_ht = ordered_qty * unit_price
                line_tax = line_ht * (tax_rate / Decimal('100.00'))

                PurchaseOrderItem.objects.create(
                    organization=tenant,
                    purchase_order=order,
                    product=product,
                    ordered_quantity=ordered_qty,
                    unit_price=unit_price,
                    tax_rate=tax_rate,
                    total_price=line_ht
                )

                total_ht += line_ht
                total_tax += line_tax

            order.total_ht = total_ht
            order.total_tax = total_tax
            order.total_ttc = total_ht + total_tax
            order.save()

    @action(detail=True, methods=['post'])
    def confirm_order(self, request, pk=None):
        order = self.get_object()
        if order.status == 'BROUILLON':
            order.status = 'COMMANDE'
            order.save()
        return Response(PurchaseOrderSerializer(order).data)

    @action(detail=True, methods=['post'])
    def receive_goods(self, request, pk=None):
        order = self.get_object()
        tenant = getattr(request, 'tenant', None)
        received_items = request.data.get('received_items', []) # [{'item_id': ..., 'quantity': ..., 'unit_cost': ...}]
        notes = request.data.get('notes', '')

        if not received_items:
            # Full reception shortcut if not specified
            received_items = [
                {
                    'item_id': str(item.id),
                    'quantity': str(item.ordered_quantity - item.received_quantity),
                    'unit_cost': str(item.unit_price)
                }
                for item in order.items.all()
                if item.received_quantity < item.ordered_quantity
            ]

        updated_order = InventoryService.receive_purchase_order_items(
            tenant=tenant,
            purchase_order=order,
            received_items=received_items,
            performed_by=request.user if request.user.is_authenticated else None,
            notes=notes
        )

        return Response(PurchaseOrderSerializer(updated_order).data)


class StockMovementViewSet(TenantQuerySetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = StockMovement.objects.select_related(
        'product', 'product__unit', 'source_warehouse', 'target_warehouse', 'performed_by'
    ).all()
    serializer_class = StockMovementSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        m_type = self.request.query_params.get('type')
        warehouse = self.request.query_params.get('warehouse')
        product = self.request.query_params.get('product')

        if m_type:
            qs = qs.filter(movement_type=m_type)
        if warehouse:
            qs = qs.filter(Q(source_warehouse_id=warehouse) | Q(target_warehouse_id=warehouse))
        if product:
            qs = qs.filter(product_id=product)

        return qs


class InventoryAuditViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = InventoryAudit.objects.select_related('warehouse').prefetch_related('items', 'items__product', 'items__product__unit').all()
    serializer_class = InventoryAuditSerializer

    def perform_create(self, serializer):
        tenant = getattr(self.request, 'tenant', None)
        audit = serializer.save(organization=tenant)
        
        # Populate items automatically with current theoretical stocks
        warehouse = audit.warehouse
        stocks = ProductStock.objects.filter(warehouse=warehouse, organization=tenant).select_related('product')
        for stock in stocks:
            InventoryAuditItem.objects.create(
                organization=tenant,
                audit=audit,
                product=stock.product,
                theoretical_quantity=stock.quantity_on_hand,
                physical_quantity=stock.quantity_on_hand, # Default to current
                unit_cost=stock.pmp_cost or stock.product.purchase_price
            )

    @action(detail=True, methods=['post'])
    def save_counts(self, request, pk=None):
        audit = self.get_object()
        tenant = getattr(request, 'tenant', None)
        counts = request.data.get('counts', []) # [{'item_id': ..., 'physical_quantity': ...}]

        for item_data in counts:
            item = InventoryAuditItem.objects.get(id=item_data['item_id'], audit=audit, organization=tenant)
            item.physical_quantity = Decimal(str(item_data['physical_quantity']))
            item.notes = item_data.get('notes', item.notes)
            item.save()

        audit.status = 'EN_COURS'
        audit.save()
        return Response(InventoryAuditSerializer(audit).data)

    @action(detail=True, methods=['post'])
    def validate_and_apply(self, request, pk=None):
        audit = self.get_object()
        tenant = getattr(request, 'tenant', None)

        validated_audit = InventoryService.validate_and_apply_audit(
            tenant=tenant,
            audit=audit,
            performed_by=request.user if request.user.is_authenticated else None
        )

        return Response(InventoryAuditSerializer(validated_audit).data)


class BillOfMaterialViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = BillOfMaterial.objects.select_related('product').prefetch_related('items', 'items__component', 'items__component__unit').all()
    serializer_class = BillOfMaterialSerializer
    search_fields = ['name', 'product__name', 'product__sku']
    filterset_fields = ['product', 'is_active']

    def perform_create(self, serializer):
        tenant = getattr(self.request, 'tenant', None)
        serializer.save(organization=tenant)


class WorkOrderViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = WorkOrder.objects.select_related('product', 'product__unit', 'bom', 'warehouse').all()
    serializer_class = WorkOrderSerializer
    search_fields = ['order_number', 'product__name', 'product__sku']
    filterset_fields = ['status', 'product', 'warehouse']

    def perform_create(self, serializer):
        tenant = getattr(self.request, 'tenant', None)
        serializer.save(organization=tenant)

    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        work_order = self.get_object()
        tenant = getattr(request, 'tenant', None)
        user = request.user
        quantity_to_build = Decimal(str(request.data.get('quantity', 0)))

        if quantity_to_build <= 0:
            return Response({"error": "La quantité doit être supérieure à 0."}, status=400)
            
        try:
            InventoryService.execute_work_order(tenant, work_order, quantity_to_build, user)
            work_order.refresh_from_db()
            return Response(WorkOrderSerializer(work_order).data)
        except ValueError as e:
            return Response({"error": str(e)}, status=400)
