from decimal import Decimal
from django.db import transaction
from rest_framework.exceptions import ValidationError
from .models import (
    Product, ProductStock, Warehouse, StockMovement, 
    PurchaseOrder, PurchaseOrderItem, InventoryAudit, InventoryAuditItem
)


class InventoryService:

    @staticmethod
    @transaction.atomic
    def process_stock_movement(
        tenant,
        product: Product,
        movement_type: str,
        quantity: Decimal,
        unit_cost: Decimal = Decimal('0.00'),
        source_warehouse: Warehouse = None,
        target_warehouse: Warehouse = None,
        reference_document: str = '',
        reason: str = '',
        performed_by = None,
        from_reservation: bool = False
    ) -> StockMovement:
        """
        Gère l'exécution atomique d'un mouvement de stock et ajuste les balances par dépôt.
        """
        if quantity <= Decimal('0.00'):
            raise ValidationError("La quantité du mouvement doit être supérieure à zéro.")

        # 1. Traitement Sorties / Transfert depuis source_warehouse
        if movement_type in ['SORTIE_VENTE', 'SORTIE_CONSOMMATION', 'SORTIE_AJUSTEMENT', 'SORTIE_REBUT', 'TRANSFERT_DEPOT']:
            if not source_warehouse:
                raise ValidationError("L'entrepôt source est requis pour ce type de mouvement.")
            
            src_stock, _ = ProductStock.objects.get_or_create(
                organization=tenant,
                product=product,
                warehouse=source_warehouse,
                defaults={'pmp_cost': product.purchase_price}
            )
            
            # Vérification de stock disponible (sauf ajustement autorisé)
            if movement_type != 'SORTIE_AJUSTEMENT':
                available_to_take = src_stock.quantity_on_hand if from_reservation else src_stock.quantity_available
                if available_to_take < quantity:
                    raise ValidationError(
                        f"Stock insuffisant dans '{source_warehouse.name}'. Disponible: {available_to_take}, Demandé: {quantity}"
                    )
            
            src_stock.quantity_on_hand -= quantity
            if from_reservation and src_stock.quantity_reserved >= quantity:
                src_stock.quantity_reserved -= quantity
            
            src_stock.save()

            if unit_cost == Decimal('0.00'):
                unit_cost = src_stock.pmp_cost or product.purchase_price

        # 2. Traitement Entrées / Transfert vers target_warehouse
        if movement_type in ['ENTREE_RECEPTION', 'ENTREE_AJUSTEMENT', 'ENTREE_RETOUR_CLIENT', 'TRANSFERT_DEPOT']:
            if not target_warehouse:
                raise ValidationError("L'entrepôt de destination est requis pour ce type de mouvement.")
            
            tgt_stock, _ = ProductStock.objects.get_or_create(
                organization=tenant,
                product=product,
                warehouse=target_warehouse,
                defaults={'pmp_cost': unit_cost or product.purchase_price}
            )

            # Calcul du CUMP / PMP lors d'une réception avec prix
            if movement_type == 'ENTREE_RECEPTION' and unit_cost > Decimal('0.00'):
                current_qty = tgt_stock.quantity_on_hand
                current_pmp = tgt_stock.pmp_cost or Decimal('0.00')
                new_total_qty = current_qty + quantity
                if new_total_qty > Decimal('0.00'):
                    new_pmp = ((current_qty * current_pmp) + (quantity * unit_cost)) / new_total_qty
                    tgt_stock.pmp_cost = round(new_pmp, 2)
            elif movement_type == 'TRANSFERT_DEPOT' and source_warehouse:
                src_stock = ProductStock.objects.filter(organization=tenant, product=product, warehouse=source_warehouse).first()
                if src_stock and src_stock.pmp_cost:
                    tgt_stock.pmp_cost = src_stock.pmp_cost

            tgt_stock.quantity_on_hand += quantity
            tgt_stock.save()

        # 3. Enregistrement du mouvement
        movement = StockMovement.objects.create(
            organization=tenant,
            product=product,
            source_warehouse=source_warehouse,
            target_warehouse=target_warehouse,
            movement_type=movement_type,
            quantity=quantity,
            unit_cost=unit_cost,
            total_cost=quantity * unit_cost,
            reference_document=reference_document,
            reason=reason,
            performed_by=performed_by
        )

        return movement

    @staticmethod
    @transaction.atomic
    def receive_purchase_order_items(
        tenant,
        purchase_order: PurchaseOrder,
        received_items: list, # [{'item_id': uuid, 'quantity': Decimal, 'unit_cost': Decimal}]
        performed_by = None,
        notes: str = ''
    ):
        """
        Traite la réception partielle ou totale d'une commande d'achat.
        """
        all_completed = True
        
        for entry in received_items:
            item_id = entry.get('item_id')
            qty_to_receive = Decimal(str(entry.get('quantity', 0)))
            cost = Decimal(str(entry.get('unit_cost', 0)))
            
            if qty_to_receive <= Decimal('0.00'):
                continue
                
            po_item = PurchaseOrderItem.objects.get(id=item_id, purchase_order=purchase_order, organization=tenant)
            
            # Update PO item received qty
            po_item.received_quantity += qty_to_receive
            po_item.save()

            if cost <= Decimal('0.00'):
                cost = po_item.unit_price

            # Create Stock Movement
            InventoryService.process_stock_movement(
                tenant=tenant,
                product=po_item.product,
                movement_type='ENTREE_RECEPTION',
                quantity=qty_to_receive,
                unit_cost=cost,
                target_warehouse=purchase_order.warehouse,
                reference_document=purchase_order.order_number,
                reason=f"Réception B.C. {purchase_order.order_number}" + (f" - {notes}" if notes else ""),
                performed_by=performed_by
            )

        # Check global order completion status
        for item in purchase_order.items.all():
            if item.received_quantity < item.ordered_quantity:
                all_completed = False
                break

        if all_completed:
            purchase_order.status = 'RECU_TOTAL'
        else:
            purchase_order.status = 'RECEPTION_PARTIELLE'
            
        purchase_order.save()
        return purchase_order

    @staticmethod
    @transaction.atomic
    def validate_and_apply_audit(
        tenant,
        audit: InventoryAudit,
        performed_by = None
    ):
        """
        Valide un inventaire physique et génère automatiquement les mouvements d'ajustement.
        """
        if audit.status == 'VALIDE':
            raise ValidationError("Cet inventaire est déjà validé et appliqué.")

        from django.utils import timezone
        total_variance_val = Decimal('0.00')

        for item in audit.items.all():
            diff = item.physical_quantity - item.theoretical_quantity
            item.variance_quantity = diff
            item.variance_cost = diff * item.unit_cost
            item.save()

            total_variance_val += item.variance_cost

            if diff > Decimal('0.00'):
                # Ajustement positif (Entrée)
                InventoryService.process_stock_movement(
                    tenant=tenant,
                    product=item.product,
                    movement_type='ENTREE_AJUSTEMENT',
                    quantity=diff,
                    unit_cost=item.unit_cost,
                    target_warehouse=audit.warehouse,
                    reference_document=audit.audit_number,
                    reason=f"Régularisation inventaire: excédent de +{diff} {item.product.unit.symbol if item.product.unit else 'u'}",
                    performed_by=performed_by
                )
            elif diff < Decimal('0.00'):
                # Ajustement négatif (Sortie)
                pos_diff = abs(diff)
                InventoryService.process_stock_movement(
                    tenant=tenant,
                    product=item.product,
                    movement_type='SORTIE_AJUSTEMENT',
                    quantity=pos_diff,
                    unit_cost=item.unit_cost,
                    source_warehouse=audit.warehouse,
                    reference_document=audit.audit_number,
                    reason=f"Régularisation inventaire: déficit de -{pos_diff} {item.product.unit.symbol if item.product.unit else 'u'}",
                    performed_by=performed_by
                )

        audit.status = 'VALIDE'
        audit.completed_date = timezone.now()
        audit.total_variance_value = total_variance_val
        audit.save()

        return audit

    @staticmethod
    @transaction.atomic
    def reserve_stock(tenant, product: Product, warehouse: Warehouse, quantity: Decimal):
        """
        Réserve une quantité de stock pour empêcher son utilisation.
        """
        if quantity <= Decimal('0.00'):
            raise ValidationError("La quantité à réserver doit être supérieure à zéro.")
            
        stock, _ = ProductStock.objects.get_or_create(
            organization=tenant,
            product=product,
            warehouse=warehouse,
            defaults={'pmp_cost': product.purchase_price}
        )
        
        if stock.quantity_available < quantity:
            raise ValidationError(
                f"Stock disponible insuffisant pour réserver. Disponible: {stock.quantity_available}, Demandé: {quantity}"
            )
            
        stock.quantity_reserved += quantity
        stock.save()
        return stock

    @staticmethod
    @transaction.atomic
    def release_reservation(tenant, product: Product, warehouse: Warehouse, quantity: Decimal):
        """
        Annule une réservation de stock.
        """
        if quantity <= Decimal('0.00'):
            raise ValidationError("La quantité à libérer doit être supérieure à zéro.")
            
        stock = ProductStock.objects.filter(organization=tenant, product=product, warehouse=warehouse).first()
        if not stock:
            raise ValidationError("Aucun stock trouvé pour ce produit dans cet entrepôt.")
            
        if stock.quantity_reserved < quantity:
            raise ValidationError(
                f"Quantité réservée inférieure à la quantité à libérer. Réservé: {stock.quantity_reserved}, Demandé: {quantity}"
            )
            
        stock.quantity_reserved -= quantity
        stock.save()
        return stock

    @staticmethod
    @transaction.atomic
    def execute_work_order(tenant, work_order, quantity_to_build: Decimal, performed_by=None):
        """
        Exécute un ordre de fabrication :
        - Consomme les matières premières selon la nomenclature (BOM).
        - Entre le produit fini en stock.
        """
        if work_order.status in ['COMPLETED', 'CANCELLED']:
            raise ValueError(f"Impossible d'exécuter un ordre au statut {work_order.get_status_display()}")

        bom = work_order.bom
        warehouse = work_order.warehouse
        
        # 1. Check & Consume Raw Materials
        for item in bom.items.all():
            qty_to_consume = item.quantity * quantity_to_build
            
            # Check availability
            stock = ProductStock.objects.filter(
                organization=tenant, product=item.component, warehouse=warehouse
            ).first()
            
            if not stock or stock.quantity_available < qty_to_consume:
                raise ValueError(f"Stock insuffisant pour le composant {item.component.name}. "
                                 f"Requis: {qty_to_consume}, Dispo: {stock.quantity_available if stock else 0}")
            
            # Consume
            InventoryService.process_stock_movement(
                tenant=tenant,
                product=item.component,
                movement_type='SORTIE_CONSOMMATION',
                quantity=qty_to_consume,
                unit_cost=stock.pmp_cost,
                source_warehouse=warehouse,
                reference_document=f"WO-{work_order.order_number}",
                reason="Consommation pour fabrication",
                performed_by=performed_by
            )
            
        # 2. Produce Finished Good
        # We need an estimated cost for the finished good based on BOM
        total_bom_cost = Decimal('0.00')
        for item in bom.items.all():
            comp_stock = ProductStock.objects.filter(
                organization=tenant, product=item.component, warehouse=warehouse
            ).first()
            if comp_stock:
                total_bom_cost += (item.quantity * comp_stock.pmp_cost)
                
        InventoryService.process_stock_movement(
            tenant=tenant,
            product=work_order.product,
            movement_type='ENTREE_RECEPTION',
            quantity=quantity_to_build,
            unit_cost=total_bom_cost,
            target_warehouse=warehouse,
            reference_document=f"WO-{work_order.order_number}",
            reason="Production terminée",
            performed_by=performed_by
        )
        
        # 3. Update Work Order
        work_order.completed_quantity += quantity_to_build
        if work_order.completed_quantity >= work_order.planned_quantity:
            work_order.status = 'COMPLETED'
            import datetime
            work_order.end_date = datetime.date.today()
        else:
            work_order.status = 'IN_PROGRESS'
            
        if not work_order.start_date:
            import datetime
            work_order.start_date = datetime.date.today()
            
        work_order.save()
        return work_order
