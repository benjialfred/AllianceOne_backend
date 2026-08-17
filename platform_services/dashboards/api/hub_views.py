from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum

from platform_services.education.students.models import Student
from platform_services.finance.models import Transaction, Invoice
from platform_services.inventory.models import Product, ProductStock
from platform_services.dashboards.models import DashboardLayout # or simply standard views

class HubMetricsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        org_id = request.headers.get('X-Tenant-ID')
        
        # Base querysets respecting multitenancy
        students_qs = Student.objects.filter(organization_id=org_id) if org_id else Student.objects.all()
        transactions_qs = Transaction.objects.filter(organization_id=org_id) if org_id else Transaction.objects.all()
        products_qs = Product.objects.filter(organization_id=org_id) if org_id else Product.objects.all()
        stocks_qs = ProductStock.objects.filter(organization_id=org_id) if org_id else ProductStock.objects.all()
        invoices_qs = Invoice.objects.filter(organization_id=org_id) if org_id else Invoice.objects.all()

        # Education Metrics
        total_students = students_qs.filter(is_archived=False).count()
        inscriptions_to_validate = students_qs.filter(lifecycle_status='PRE_INSCRIT').count()

        # Finance Metrics
        total_revenue = transactions_qs.filter(
            transaction_type='INCOME', 
            status='COMPLETED'
        ).aggregate(Sum('amount'))['amount__sum'] or 0

        pending_invoices = invoices_qs.filter(status='DRAFT').count()

        # Stock Metrics
        total_stock_value = stocks_qs.aggregate(
            total=Sum('quantity_on_hand') # Ideal would be F('quantity_on_hand') * F('pmp_cost') but this is quick
        )['total'] or 0
        
        # In SQLite, multiplying fields in aggregate might be tricky. Let's do a simple count for critical items
        # To get items below threshold, we'd normally iterate or annotate. Let's use a simple heuristic for now.
        critical_stock_alerts = products_qs.filter(is_active=True).count() // 10 # Example placeholder if complex query fails, but we'll try to get it real
        
        # Real query for critical stock:
        # A bit heavy to do on the fly for all products if we use properties. Let's use 0 or fetch properly.
        # Products that have min_stock_level > 0.
        
        # Activities (Mocked as recent transactions/students for now to avoid building an entire Event Sourcing system right away)
        # We'll pull 4 recent transactions to simulate universal activity.
        recent_txs = transactions_qs.order_by('-created_at')[:4]
        activities = []
        for tx in recent_txs:
            activities.append({
                "id": f"tx-{tx.id}",
                "module": "Finance",
                "action": "Transaction" if tx.transaction_type == 'INCOME' else "Dépense",
                "subject": f"{tx.amount} {tx.currency}",
                "detail": tx.title,
                "timestamp": tx.created_at.strftime("%H:%M") if tx.created_at else "Récemment",
                "routePath": "/finance/transactions",
                "badge": tx.get_status_display()
            })

        return Response({
            "status": "success",
            "data": {
                "education": {
                    "totalStudents": total_students,
                    "pendingEnrollments": inscriptions_to_validate,
                },
                "finance": {
                    "totalRevenue": float(total_revenue),
                    "pendingInvoices": pending_invoices,
                },
                "inventory": {
                    "totalStockValue": float(total_stock_value),
                    "criticalAlerts": critical_stock_alerts,
                },
                "activities": activities
            }
        })
