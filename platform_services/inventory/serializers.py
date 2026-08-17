from rest_framework import serializers
from .models import (
    Category, Unit, Warehouse, WarehouseLocation,
    Product, ProductStock, Supplier, ProductBatch, ProductSupplier, SerialNumber,
    PurchaseOrder, PurchaseOrderItem,
    StockMovement, InventoryAudit, InventoryAuditItem,
    BillOfMaterial, BOMItem, WorkOrder
)


class CategorySerializer(serializers.ModelSerializer):
    products_count = serializers.IntegerField(source='products.count', read_only=True)

    class Meta:
        model = Category
        fields = ['id', 'name', 'code', 'description', 'parent', 'products_count', 'created_at']


class UnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Unit
        fields = ['id', 'name', 'symbol', 'description', 'created_at']


class WarehouseLocationSerializer(serializers.ModelSerializer):
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)

    class Meta:
        model = WarehouseLocation
        fields = ['id', 'warehouse', 'warehouse_name', 'code', 'zone', 'aisle', 'shelf', 'bin', 'created_at']


class WarehouseSerializer(serializers.ModelSerializer):
    locations_count = serializers.IntegerField(source='locations.count', read_only=True)
    total_stock_items = serializers.SerializerMethodField()
    total_stock_value = serializers.SerializerMethodField()

    class Meta:
        model = Warehouse
        fields = [
            'id', 'code', 'name', 'address', 'city', 'manager_name', 'phone', 
            'is_default', 'is_active', 'capacity_m3', 'locations_count', 
            'total_stock_items', 'total_stock_value', 'created_at'
        ]

    def get_total_stock_items(self, obj):
        return sum(s.quantity_on_hand for s in obj.stocks.all())

    def get_total_stock_value(self, obj):
        return sum(s.total_value for s in obj.stocks.all())


class ProductStockSerializer(serializers.ModelSerializer):
    warehouse_code = serializers.CharField(source='warehouse.code', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    location_code = serializers.CharField(source='location.code', read_only=True, allow_null=True)
    quantity_available = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    total_value = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = ProductStock
        fields = [
            'id', 'product', 'warehouse', 'warehouse_code', 'warehouse_name',
            'location', 'location_code', 'quantity_on_hand', 'quantity_reserved',
            'quantity_available', 'pmp_cost', 'total_value', 'updated_at'
        ]


class ProductBatchSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    is_expired = serializers.SerializerMethodField()

    class Meta:
        model = ProductBatch
        fields = [
            'id', 'product', 'product_name', 'product_sku', 'batch_number',
            'manufacturing_date', 'expiry_date', 'best_before_date',
            'current_quantity', 'is_expired', 'created_at', 'updated_at'
        ]

    def get_is_expired(self, obj):
        from django.utils import timezone
        if obj.expiry_date:
            return obj.expiry_date < timezone.now().date()
        return False


class SerialNumberSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    batch_number = serializers.CharField(source='batch.batch_number', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = SerialNumber
        fields = [
            'id', 'product', 'product_name', 'batch', 'batch_number',
            'warehouse', 'warehouse_name', 'serial_number', 'status',
            'status_display', 'created_at', 'updated_at'
        ]


class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    unit_name = serializers.CharField(source='unit.name', read_only=True)
    unit_symbol = serializers.CharField(source='unit.symbol', read_only=True)
    total_stock_on_hand = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    total_stock_available = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    total_valuation = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    stock_status = serializers.CharField(read_only=True)
    stocks = ProductStockSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'sku', 'barcode', 'name', 'description', 'category', 'category_name',
            'unit', 'unit_name', 'unit_symbol', 'purchase_price', 'selling_price',
            'min_stock_level', 'max_stock_level', 'reorder_quantity', 'image',
            'tracking_serial', 'is_active', 'total_stock_on_hand', 'total_stock_available', 'total_valuation',
            'stock_status', 'stocks', 'created_at', 'updated_at'
        ]


class SupplierSerializer(serializers.ModelSerializer):
    orders_count = serializers.IntegerField(source='purchase_orders.count', read_only=True)

    class Meta:
        model = Supplier
        fields = [
            'id', 'code', 'name', 'contact_name', 'email', 'phone', 'address',
            'city', 'payment_terms', 'tax_id', 'rating', 'notes', 'is_active',
            'orders_count', 'created_at'
        ]


class ProductSupplierSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)

    class Meta:
        model = ProductSupplier
        fields = [
            'id', 'product', 'product_name', 'product_sku',
            'supplier', 'supplier_name', 'supplier_product_code',
            'purchase_price', 'lead_time_days', 'is_primary'
        ]


class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    unit_symbol = serializers.CharField(source='product.unit.symbol', read_only=True, default='u')

    class Meta:
        model = PurchaseOrderItem
        fields = [
            'id', 'purchase_order', 'product', 'product_sku', 'product_name',
            'unit_symbol', 'ordered_quantity', 'received_quantity', 'unit_price',
            'tax_rate', 'total_price'
        ]


class PurchaseOrderSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    items = PurchaseOrderItemSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = PurchaseOrder
        fields = [
            'id', 'order_number', 'supplier', 'supplier_name', 'warehouse', 'warehouse_name',
            'status', 'status_display', 'order_date', 'expected_delivery_date', 'notes',
            'total_ht', 'total_tax', 'total_ttc', 'items', 'created_at'
        ]


class StockMovementSerializer(serializers.ModelSerializer):
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    unit_symbol = serializers.CharField(source='product.unit.symbol', read_only=True, default='u')
    source_warehouse_name = serializers.CharField(source='source_warehouse.name', read_only=True, allow_null=True)
    target_warehouse_name = serializers.CharField(source='target_warehouse.name', read_only=True, allow_null=True)
    movement_type_display = serializers.CharField(source='get_movement_type_display', read_only=True)
    performed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = StockMovement
        fields = [
            'id', 'movement_number', 'product', 'product_sku', 'product_name', 'unit_symbol',
            'source_warehouse', 'source_warehouse_name', 'target_warehouse', 'target_warehouse_name',
            'movement_type', 'movement_type_display', 'quantity', 'unit_cost', 'total_cost',
            'reference_document', 'reason', 'performed_by', 'performed_by_name', 'created_at'
        ]

    def get_performed_by_name(self, obj):
        if obj.performed_by:
            return getattr(obj.performed_by, 'get_full_name', lambda: str(obj.performed_by))() or str(obj.performed_by)
        return "Système"


class InventoryAuditItemSerializer(serializers.ModelSerializer):
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    unit_symbol = serializers.CharField(source='product.unit.symbol', read_only=True, default='u')

    class Meta:
        model = InventoryAuditItem
        fields = [
            'id', 'audit', 'product', 'product_sku', 'product_name', 'unit_symbol',
            'theoretical_quantity', 'physical_quantity', 'variance_quantity',
            'unit_cost', 'variance_cost', 'notes'
        ]


class InventoryAuditSerializer(serializers.ModelSerializer):
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    items = InventoryAuditItemSerializer(many=True, read_only=True)
    items_count = serializers.IntegerField(source='items.count', read_only=True)

    class Meta:
        model = InventoryAudit
        fields = [
            'id', 'audit_number', 'title', 'warehouse', 'warehouse_name',
            'status', 'status_display', 'scheduled_date', 'completed_date',
            'responsible_name', 'notes', 'total_variance_value', 'items_count', 'items', 'created_at'
        ]


class BOMItemSerializer(serializers.ModelSerializer):
    component_name = serializers.CharField(source='component.name', read_only=True)
    component_sku = serializers.CharField(source='component.sku', read_only=True)
    unit_symbol = serializers.CharField(source='component.unit.symbol', read_only=True)

    class Meta:
        model = BOMItem
        fields = [
            'id', 'bom', 'component', 'component_name', 'component_sku', 'unit_symbol', 'quantity'
        ]


class BillOfMaterialSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    items = BOMItemSerializer(many=True, read_only=True)

    class Meta:
        model = BillOfMaterial
        fields = [
            'id', 'product', 'product_name', 'product_sku', 'name', 'version', 'is_active', 'items'
        ]


class WorkOrderSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    bom_name = serializers.CharField(source='bom.name', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    unit_symbol = serializers.CharField(source='product.unit.symbol', read_only=True)

    class Meta:
        model = WorkOrder
        fields = [
            'id', 'order_number', 'product', 'product_name', 'product_sku', 'unit_symbol',
            'bom', 'bom_name', 'warehouse', 'warehouse_name',
            'planned_quantity', 'completed_quantity', 'status', 'status_display',
            'start_date', 'end_date', 'notes', 'created_at', 'updated_at'
        ]
