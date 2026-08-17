from decimal import Decimal
from django.db import transaction
from django.db.models import F
from .models import Product, ProductSupplier, PurchaseOrder, PurchaseOrderItem, Warehouse

def generate_auto_replenishment_orders(tenant):
    """
    Génère des brouillons de bons de commande pour les produits en rupture ou stock bas.
    Regroupe les produits par fournisseur principal.
    """
    # Récupérer les produits sous leur seuil d'alerte
    products = Product.objects.filter(organization=tenant)
    low_stock_products = []
    
    for p in products:
        if p.stock_status in ['OUT_OF_STOCK', 'LOW_STOCK']:
            low_stock_products.append(p)
            
    if not low_stock_products:
        return 0
        
    # Grouper par fournisseur principal
    supplier_orders = {} # supplier -> list of items to order
    
    for product in low_stock_products:
        # Trouver le fournisseur principal
        primary_supplier_link = ProductSupplier.objects.filter(
            organization=tenant, 
            product=product, 
            is_primary=True
        ).first()
        
        # Si pas de fournisseur principal, prendre le premier disponible
        if not primary_supplier_link:
            primary_supplier_link = ProductSupplier.objects.filter(
                organization=tenant, 
                product=product
            ).first()
            
        if not primary_supplier_link:
            continue # Produit sans fournisseur
            
        supplier = primary_supplier_link.supplier
        
        # Calculer la quantité à commander
        # Soit reorder_quantity, soit la quantité nécessaire pour atteindre max_stock_level
        qty_to_order = product.reorder_quantity
        if qty_to_order <= 0:
            qty_to_order = product.max_stock_level - product.total_stock_on_hand
            if qty_to_order <= 0:
                qty_to_order = Decimal('10.00')
                
        if supplier not in supplier_orders:
            supplier_orders[supplier] = []
            
        supplier_orders[supplier].append({
            'product': product,
            'qty': qty_to_order,
            'unit_price': primary_supplier_link.purchase_price
        })
        
    # Default warehouse
    default_warehouse = Warehouse.objects.filter(organization=tenant, is_default=True).first()
    if not default_warehouse:
        default_warehouse = Warehouse.objects.filter(organization=tenant).first()
        
    if not default_warehouse:
        return 0

    orders_created = 0
    
    with transaction.atomic():
        for supplier, items in supplier_orders.items():
            # Créer le bon de commande brouillon
            po = PurchaseOrder.objects.create(
                organization=tenant,
                supplier=supplier,
                warehouse=default_warehouse,
                status='BROUILLON',
                notes='Généré automatiquement par le moteur de réassort.'
            )
            
            total_ht = Decimal('0.00')
            for item in items:
                po_item = PurchaseOrderItem.objects.create(
                    organization=tenant,
                    purchase_order=po,
                    product=item['product'],
                    ordered_quantity=item['qty'],
                    unit_price=item['unit_price']
                )
                total_ht += po_item.total_price
                
            po.total_ht = total_ht
            po.total_ttc = total_ht * Decimal('1.1925') # Assuming 19.25% tax
            po.save()
            orders_created += 1
            
    return orders_created
