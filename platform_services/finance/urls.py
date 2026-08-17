from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    FinancialAccountViewSet, FinancialCategoryViewSet,
    TransactionViewSet, BudgetViewSet, InvoiceViewSet,
    TontineGroupViewSet, TontineMemberViewSet,
    TontineRoundViewSet, TontineContributionViewSet,
    TontinePayoutViewSet
)
from .dashboard_views import FinanceDashboardView

router = DefaultRouter()
router.register(r'accounts', FinancialAccountViewSet, basename='finance-accounts')
router.register(r'categories', FinancialCategoryViewSet, basename='finance-categories')
router.register(r'transactions', TransactionViewSet, basename='finance-transactions')
router.register(r'budgets', BudgetViewSet, basename='finance-budgets')
router.register(r'invoices', InvoiceViewSet, basename='finance-invoices')
router.register(r'tontines', TontineGroupViewSet, basename='finance-tontines')
router.register(r'tontine-members', TontineMemberViewSet, basename='finance-tontine-members')
router.register(r'tontine-rounds', TontineRoundViewSet, basename='finance-tontine-rounds')
router.register(r'tontine-contributions', TontineContributionViewSet, basename='finance-tontine-contributions')
router.register(r'tontine-payouts', TontinePayoutViewSet, basename='finance-tontine-payouts')

urlpatterns = [
    path('dashboard/stats/', FinanceDashboardView.as_view(), name='finance-dashboard-stats'),
    path('', include(router.urls)),
]
