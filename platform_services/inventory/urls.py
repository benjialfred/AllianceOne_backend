from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    CategoryViewSet, UnitViewSet, WarehouseViewSet, WarehouseLocationViewSet,
    ProductViewSet, SupplierViewSet, PurchaseOrderViewSet,
    StockMovementViewSet, InventoryAuditViewSet, ProductBatchViewSet,
    ProductSupplierViewSet, SerialNumberViewSet,
    BillOfMaterialViewSet, WorkOrderViewSet
)
from .dashboard_views import (
    InventoryDashboardKPIView,
    InventoryDashboardIntelligenceView,
    InventoryDashboardTimelineView
)

router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'units', UnitViewSet, basename='unit')
router.register(r'warehouses', WarehouseViewSet, basename='warehouse')
router.register(r'locations', WarehouseLocationViewSet, basename='warehouse-location')
router.register(r'products', ProductViewSet, basename='product')
router.register(r'product-batches', ProductBatchViewSet, basename='product-batch')
router.register(r'product-suppliers', ProductSupplierViewSet, basename='product-supplier')
router.register(r'serial-numbers', SerialNumberViewSet, basename='serial-number')
router.register(r'suppliers', SupplierViewSet, basename='supplier')
router.register(r'purchase-orders', PurchaseOrderViewSet, basename='purchase-order')
router.register(r'stock-movements', StockMovementViewSet, basename='stock-movement')
router.register(r'audits', InventoryAuditViewSet, basename='inventory-audit')
router.register(r'boms', BillOfMaterialViewSet, basename='bom')
router.register(r'work-orders', WorkOrderViewSet, basename='work-order')

urlpatterns = [
    path('', include(router.urls)),
    path('dashboard-stats/kpis/', InventoryDashboardKPIView.as_view(), name='inventory-dashboard-kpis'),
    path('dashboard-stats/intelligence/', InventoryDashboardIntelligenceView.as_view(), name='inventory-dashboard-intelligence'),
    path('dashboard-stats/timeline/', InventoryDashboardTimelineView.as_view(), name='inventory-dashboard-timeline'),
]
