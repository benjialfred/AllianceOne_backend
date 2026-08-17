import uuid
from decimal import Decimal
from django.db import models
from django.conf import settings
from platform_services.identity.models import TenantModel


class Category(TenantModel):
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True, null=True)
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='children')

    class Meta:
        verbose_name = "Catégorie"
        verbose_name_plural = "Catégories"
        ordering = ['name']

    def __str__(self):
        return self.name


class Unit(TenantModel):
    name = models.CharField(max_length=100) # e.g. "Unité", "Kilogramme", "Carton de 24", "Litre"
    symbol = models.CharField(max_length=20) # e.g. "U", "kg", "ctn", "L"
    description = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        verbose_name = "Unité de mesure"
        verbose_name_plural = "Unités de mesure"
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.symbol})"


class Warehouse(TenantModel):
    code = models.CharField(max_length=50) # e.g. "DEP-01", "MAG-CENTRAL"
    name = models.CharField(max_length=200)
    address = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    manager_name = models.CharField(max_length=150, blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    capacity_m3 = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    class Meta:
        verbose_name = "Entrepôt / Dépôt"
        verbose_name_plural = "Entrepôts / Dépôts"
        ordering = ['name']

    def __str__(self):
        return f"{self.name} [{self.code}]"


class WarehouseLocation(TenantModel):
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='locations')
    code = models.CharField(max_length=50) # e.g. "A1-03-B"
    zone = models.CharField(max_length=50, blank=True, null=True) # e.g. "Zone Frais", "Zone A"
    aisle = models.CharField(max_length=20, blank=True, null=True) # Allée
    shelf = models.CharField(max_length=20, blank=True, null=True) # Étagère
    bin = models.CharField(max_length=20, blank=True, null=True) # Bac

    class Meta:
        verbose_name = "Emplacement"
        verbose_name_plural = "Emplacements"
        ordering = ['warehouse', 'code']

    def __str__(self):
        return f"{self.warehouse.code} - {self.code}"


class Product(TenantModel):
    sku = models.CharField(max_length=100) # SKU / Référence interne
    barcode = models.CharField(max_length=100, blank=True, null=True) # EAN / Code-barres
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, null=True, blank=True, related_name='products')
    
    # Financials
    purchase_price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00')) # Prix d'achat standard / dernier prix
    selling_price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00')) # Prix de vente catalogue
    
    # Thresholds
    min_stock_level = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('5.00')) # Seuil alerte
    max_stock_level = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('100.00'))
    reorder_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('20.00')) # Qte conseillée
    
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    tracking_serial = models.BooleanField(default=False, help_text="Exige le suivi par numéro de série unique")
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Article / Produit"
        verbose_name_plural = "Articles / Produits"
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.sku})"

    @property
    def total_stock_on_hand(self):
        return sum(s.quantity_on_hand for s in self.stocks.all()) or Decimal('0.00')

    @property
    def total_stock_available(self):
        return sum(s.quantity_available for s in self.stocks.all()) or Decimal('0.00')

    @property
    def total_valuation(self):
        return sum(s.total_value for s in self.stocks.all()) or Decimal('0.00')

    @property
    def stock_status(self):
        total = self.total_stock_on_hand
        if total <= Decimal('0.00'):
            return 'OUT_OF_STOCK'
        elif total <= self.min_stock_level:
            return 'LOW_STOCK'
        return 'IN_STOCK'


class ProductBatch(TenantModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='batches')
    batch_number = models.CharField(max_length=100)
    manufacturing_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True) # DLC
    best_before_date = models.DateField(null=True, blank=True) # DLUO
    current_quantity = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    
    class Meta:
        verbose_name = "Lot Produit"
        verbose_name_plural = "Lots Produits"
        unique_together = ('organization', 'product', 'batch_number')

    def __str__(self):
        return f"{self.product.name} - Lot {self.batch_number}"


class SerialNumber(TenantModel):
    STATUS_CHOICES = (
        ('IN_STOCK', 'En stock'),
        ('SOLD', 'Vendu / Sorti'),
        ('IN_TRANSIT', 'En transit'),
        ('LOST', 'Perdu / Rebut')
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='serial_numbers')
    batch = models.ForeignKey(ProductBatch, on_delete=models.SET_NULL, null=True, blank=True, related_name='serial_numbers')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.SET_NULL, null=True, blank=True, related_name='serial_numbers')
    serial_number = models.CharField(max_length=150)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='IN_STOCK')

    class Meta:
        verbose_name = "Numéro de Série"
        verbose_name_plural = "Numéros de Série"
        unique_together = ('organization', 'product', 'serial_number')

    def __str__(self):
        return f"{self.product.name} - SN: {self.serial_number}"

class ProductStock(TenantModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='stocks')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='stocks')
    location = models.ForeignKey(WarehouseLocation, on_delete=models.SET_NULL, null=True, blank=True, related_name='stocks')
    quantity_on_hand = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    quantity_reserved = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    pmp_cost = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00')) # Prix Moyen Pondéré

    class Meta:
        verbose_name = "Stock Produit par Dépôt"
        verbose_name_plural = "Stocks Produits par Dépôt"
        unique_together = ('organization', 'product', 'warehouse')

    def __str__(self):
        return f"{self.product.name} @ {self.warehouse.name} : {self.quantity_on_hand}"

    @property
    def quantity_available(self):
        return max(Decimal('0.00'), self.quantity_on_hand - self.quantity_reserved)

    @property
    def total_value(self):
        return self.quantity_on_hand * self.pmp_cost


class Supplier(TenantModel):
    code = models.CharField(max_length=50) # e.g. "FOURN-001"
    name = models.CharField(max_length=200)
    contact_name = models.CharField(max_length=150, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    payment_terms = models.CharField(max_length=100, default="30 jours fin de mois") # e.g. "Comptant", "30 jours"
    tax_id = models.CharField(max_length=100, blank=True, null=True) # NIF / SIRET
    rating = models.IntegerField(default=5)
    notes = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Fournisseur"
        verbose_name_plural = "Fournisseurs"
        ordering = ['name']

    def __str__(self):
        return self.name


class ProductSupplier(TenantModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='suppliers')
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='supplied_products')
    supplier_product_code = models.CharField(max_length=100, blank=True, null=True)
    purchase_price = models.DecimalField(max_digits=12, decimal_places=2)
    lead_time_days = models.IntegerField(default=0)
    is_primary = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Fournisseur d'Article"
        verbose_name_plural = "Fournisseurs d'Articles"
        unique_together = ('organization', 'product', 'supplier')

    def __str__(self):
        return f"{self.supplier.name} - {self.product.name}"


class PurchaseOrder(TenantModel):
    STATUS_CHOICES = (
        ('BROUILLON', 'Brouillon'),
        ('COMMANDE', 'Commandé'),
        ('RECEPTION_PARTIELLE', 'Réception partielle'),
        ('RECU_TOTAL', 'Réception totale'),
        ('ANNULE', 'Annulé'),
    )

    order_number = models.CharField(max_length=50, unique=True, blank=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name='purchase_orders')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name='purchase_orders')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='BROUILLON')
    order_date = models.DateField(auto_now_add=True)
    expected_delivery_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    total_ht = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    total_tax = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    total_ttc = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = "Bon de Commande Fournisseur"
        verbose_name_plural = "Bons de Commande Fournisseurs"
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.order_number:
            import datetime
            year = datetime.datetime.now().year
            self.order_number = f"BC-{year}-{uuid.uuid4().hex[:6].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.order_number} - {self.supplier.name} ({self.get_status_display()})"


class PurchaseOrderItem(TenantModel):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='purchase_items')
    ordered_quantity = models.DecimalField(max_digits=10, decimal_places=2)
    received_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    unit_price = models.DecimalField(max_digits=12, decimal_places=2) # Prix unitaire HT
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('19.25')) # TVA %
    total_price = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))

    class Meta:
        verbose_name = "Ligne de Commande Fournisseur"
        verbose_name_plural = "Lignes de Commande Fournisseurs"

    def save(self, *args, **kwargs):
        self.total_price = self.ordered_quantity * self.unit_price
        super().save(*args, **kwargs)


class StockMovement(TenantModel):
    MOVEMENT_TYPES = (
        ('ENTREE_RECEPTION', 'Entrée Réception Fournisseur'),
        ('ENTREE_AJUSTEMENT', 'Entrée Ajustement Positif'),
        ('ENTREE_RETOUR_CLIENT', 'Entrée Retour Client'),
        ('SORTIE_VENTE', 'Sortie Expédition Vente'),
        ('SORTIE_CONSOMMATION', 'Sortie Consommation Interne'),
        ('SORTIE_AJUSTEMENT', 'Sortie Ajustement Négatif'),
        ('SORTIE_REBUT', 'Sortie Perte / Rebut'),
        ('TRANSFERT_DEPOT', 'Transfert Inter-Dépôts'),
    )

    movement_number = models.CharField(max_length=60, unique=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='movements')
    batch = models.ForeignKey(ProductBatch, on_delete=models.SET_NULL, null=True, blank=True, related_name='movements')
    serial_numbers = models.ManyToManyField(SerialNumber, blank=True, related_name='movements')
    source_warehouse = models.ForeignKey(Warehouse, on_delete=models.SET_NULL, null=True, blank=True, related_name='outbound_movements')
    target_warehouse = models.ForeignKey(Warehouse, on_delete=models.SET_NULL, null=True, blank=True, related_name='inbound_movements')
    movement_type = models.CharField(max_length=40, choices=MOVEMENT_TYPES)
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    total_cost = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    reference_document = models.CharField(max_length=100, blank=True, null=True) # e.g. "BC-2026-004", "INV-2026-01"
    reason = models.TextField(blank=True, null=True)
    performed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = "Mouvement de Stock"
        verbose_name_plural = "Mouvements de Stock"
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.movement_number:
            import datetime
            year = datetime.datetime.now().year
            self.movement_number = f"MVT-{year}-{uuid.uuid4().hex[:7].upper()}"
        if not self.total_cost:
            self.total_cost = self.quantity * self.unit_cost
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.movement_number} - {self.get_movement_type_display()} : {self.product.name} ({self.quantity})"


class InventoryAudit(TenantModel):
    STATUS_CHOICES = (
        ('PLANIFIE', 'Planifié'),
        ('EN_COURS', 'Comptage en cours'),
        ('VALIDE', 'Validé & Régularisé'),
        ('ANNULE', 'Annulé'),
    )

    audit_number = models.CharField(max_length=50, unique=True, blank=True)
    title = models.CharField(max_length=200)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='audits')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='PLANIFIE')
    scheduled_date = models.DateField()
    completed_date = models.DateTimeField(null=True, blank=True)
    responsible_name = models.CharField(max_length=150, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    total_variance_value = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))

    class Meta:
        verbose_name = "Session d'Inventaire Physique"
        verbose_name_plural = "Sessions d'Inventaires Physiques"
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.audit_number:
            import datetime
            year = datetime.datetime.now().year
            self.audit_number = f"INV-{year}-{uuid.uuid4().hex[:6].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.audit_number} - {self.title} ({self.warehouse.name})"


class InventoryAuditItem(TenantModel):
    audit = models.ForeignKey(InventoryAudit, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='audit_items')
    theoretical_quantity = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    physical_quantity = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    variance_quantity = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    variance_cost = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    notes = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        verbose_name = "Ligne d'inventaire physique"
        verbose_name_plural = "Lignes d'inventaire physique"

    def save(self, *args, **kwargs):
        self.variance_quantity = self.physical_quantity - self.theoretical_quantity
        self.variance_cost = self.variance_quantity * self.unit_cost
        super().save(*args, **kwargs)


# ---------------------------------------------------------
# MANUFACTURING & WMS (Bill of Materials & Work Orders)
# ---------------------------------------------------------

class BillOfMaterial(TenantModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='boms')
    name = models.CharField(max_length=255)
    version = models.CharField(max_length=50, default='1.0')
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Nomenclature (BOM)"
        verbose_name_plural = "Nomenclatures (BOM)"
        unique_together = ('organization', 'product', 'version')

    def __str__(self):
        return f"{self.product.name} - BOM {self.version}"


class BOMItem(TenantModel):
    bom = models.ForeignKey(BillOfMaterial, on_delete=models.CASCADE, related_name='items')
    component = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='used_in_boms')
    quantity = models.DecimalField(max_digits=10, decimal_places=4)

    class Meta:
        verbose_name = "Composant de Nomenclature"
        verbose_name_plural = "Composants de Nomenclature"

    def __str__(self):
        return f"{self.quantity} x {self.component.name} (for {self.bom.product.name})"


class WorkOrder(TenantModel):
    STATUS_CHOICES = (
        ('PLANNED', 'Planifié'),
        ('IN_PROGRESS', 'En cours'),
        ('COMPLETED', 'Terminé'),
        ('CANCELLED', 'Annulé')
    )
    order_number = models.CharField(max_length=60, unique=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='work_orders')
    bom = models.ForeignKey(BillOfMaterial, on_delete=models.PROTECT)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT)
    planned_quantity = models.DecimalField(max_digits=10, decimal_places=2)
    completed_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='PLANNED')
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Ordre de Fabrication"
        verbose_name_plural = "Ordres de Fabrication"
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.order_number:
            import datetime
            year = datetime.datetime.now().year
            self.order_number = f"WO-{year}-{uuid.uuid4().hex[:6].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.order_number} - {self.product.name} ({self.get_status_display()})"
