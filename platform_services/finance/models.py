import uuid
from decimal import Decimal
from django.db import models
from django.conf import settings
from platform_services.identity.models import TenantModel


CURRENCY_CHOICES = (
    ('EUR', 'Euro (€)'),
    ('USD', 'Dollar Américain ($)'),
    ('XOF', 'Franc CFA (F.CFA)'),
    ('GBP', 'Livre Sterling (£)'),
    ('CAD', 'Dollar Canadien ($ CA)'),
    ('CHF', 'Franc Suisse (CHF)'),
)

ACCOUNT_TYPES = (
    ('BANK', 'Compte Bancaire'),
    ('CASH', 'Caisse Espèces'),
    ('MOBILE_MONEY', 'Mobile Money (Orange, Wave, MTN...)'),
    ('ONLINE', 'Passerelle / En Ligne (Stripe, PayPal...)'),
    ('SAVINGS', 'Épargne & Trésorerie Plafonnée'),
    ('OTHER', 'Autre Compte'),
)

CATEGORY_TYPES = (
    ('INCOME', 'Revenu / Recette'),
    ('EXPENSE', 'Dépense / Décaissement'),
)

TRANSACTION_TYPES = (
    ('INCOME', 'Recette / Encaissement'),
    ('EXPENSE', 'Dépense / Paiement'),
    ('TRANSFER', 'Virement Interne (Compte à Compte)'),
)

PAYMENT_METHODS = (
    ('TRANSFER', 'Virement Bancaire'),
    ('CARD', 'Carte Bancaire'),
    ('CASH', 'Espèces'),
    ('CHECK', 'Chèque'),
    ('MOBILE_MONEY', 'Mobile Money'),
    ('DIRECT_DEBIT', 'Prélèvement Automatique'),
    ('ONLINE', 'Paiement en ligne'),
    ('OTHER', 'Autre'),
)

TRANSACTION_STATUS = (
    ('COMPLETED', 'Validé / Exécuté'),
    ('PENDING', 'En Attente / Rapprochement'),
    ('CANCELLED', 'Annulé'),
)

BUDGET_PERIODS = (
    ('MONTHLY', 'Mensuel'),
    ('QUARTERLY', 'Trimestriel'),
    ('YEARLY', 'Annuel'),
    ('CUSTOM', 'Personnalisé'),
)

INVOICE_TYPES = (
    ('OUTGOING', 'Facture Client (Vente)'),
    ('INCOMING', 'Facture Fournisseur (Achat)'),
    ('QUOTATION', 'Devis / Proforma'),
)

INVOICE_STATUS = (
    ('DRAFT', 'Brouillon'),
    ('SENT', 'Émise / Transmise'),
    ('PARTIAL', 'Partiellement Payée'),
    ('PAID', 'Payée Intégralement'),
    ('OVERDUE', 'En Retard'),
    ('CANCELLED', 'Annulée'),
)


class FinancialAccount(TenantModel):
    """
    Compte financier de l'entreprise (Banques, Caisses, Portefeuilles électroniques).
    """
    name = models.CharField(max_length=150, help_text="Ex: Compte Courant BNP, Caisse Siège, Orange Money Pro")
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES, default='BANK')
    account_number = models.CharField(max_length=100, blank=True, null=True, help_text="IBAN, RIB ou numéro de compte")
    institution_name = models.CharField(max_length=150, blank=True, null=True, help_text="Nom de la banque ou du fournisseur")
    currency = models.CharField(max_length=10, choices=CURRENCY_CHOICES, default='EUR')
    initial_balance = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    current_balance = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    color = models.CharField(max_length=20, default='#3B82F6', help_text="Code couleur hex pour le badge UI")
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False, help_text="Compte sélectionné par défaut")
    description = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Compte Financier"
        verbose_name_plural = "Comptes Financiers"
        ordering = ['-is_default', 'name']

    def __str__(self):
        return f"{self.name} ({self.currency}) - Solde: {self.current_balance:,.2f}"


class FinancialCategory(TenantModel):
    """
    Catégorie budgétaire et comptable pour le classement des revenus et des dépenses.
    """
    name = models.CharField(max_length=150)
    category_type = models.CharField(max_length=10, choices=CATEGORY_TYPES, default='EXPENSE')
    code = models.CharField(max_length=50, blank=True, null=True, help_text="Code analytique ou comptable")
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='subcategories')
    color = models.CharField(max_length=20, default='#10B981')
    icon = models.CharField(max_length=50, default='Folder')
    description = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Catégorie Financière"
        verbose_name_plural = "Catégories Financières"
        ordering = ['category_type', 'name']

    def __str__(self):
        prefix = "[+]" if self.category_type == 'INCOME' else "[-]"
        return f"{prefix} {self.name}"


class Transaction(TenantModel):
    """
    Mouvement financier unitaire (Dépense, Revenu ou Virement inter-comptes).
    """
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES, default='EXPENSE')
    title = models.CharField(max_length=200, help_text="Libellé de l'opération")
    account = models.ForeignKey(FinancialAccount, on_delete=models.CASCADE, related_name='transactions', help_text="Compte source / principal")
    destination_account = models.ForeignKey(FinancialAccount, on_delete=models.SET_NULL, null=True, blank=True, related_name='incoming_transfers', help_text="Compte cible (si virement)")
    category = models.ForeignKey(FinancialCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
    
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=10, choices=CURRENCY_CHOICES, default='EUR')
    destination_amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True, help_text="Montant reçu si transfert multidevises")
    exchange_rate = models.DecimalField(max_digits=10, decimal_places=4, default=Decimal('1.0000'))
    
    date = models.DateField(help_text="Date de l'opération")
    reference_number = models.CharField(max_length=100, blank=True, null=True, help_text="Numéro de pièce / reçu / virement")
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='TRANSFER')
    payee_payer = models.CharField(max_length=200, blank=True, null=True, help_text="Tiers concerné (Client, Fournisseur, Bénéficiaire...)")
    status = models.CharField(max_length=15, choices=TRANSACTION_STATUS, default='COMPLETED')
    
    notes = models.TextField(blank=True, null=True)
    receipt_url = models.CharField(max_length=500, blank=True, null=True, help_text="URL du justificatif ou facture scannée")
    is_reconciled = models.BooleanField(default=False, help_text="Rapproché avec le relevé bancaire")
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = "Transaction Financière"
        verbose_name_plural = "Transactions Financières"
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.date} | {self.get_transaction_type_display()} | {self.title} | {self.amount} {self.currency}"


class Budget(TenantModel):
    """
    Enveloppe budgétaire prévisionnelle par catégorie de dépenses.
    """
    name = models.CharField(max_length=150)
    category = models.ForeignKey(FinancialCategory, on_delete=models.CASCADE, related_name='budgets')
    allocated_amount = models.DecimalField(max_digits=14, decimal_places=2, help_text="Montant alloué")
    currency = models.CharField(max_length=10, choices=CURRENCY_CHOICES, default='EUR')
    period = models.CharField(max_length=20, choices=BUDGET_PERIODS, default='MONTHLY')
    start_date = models.DateField()
    end_date = models.DateField()
    alert_threshold_percentage = models.IntegerField(default=80, help_text="Seuil d'alerte en pourcentage (ex: 80%)")
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Budget Prévisionnel"
        verbose_name_plural = "Budgets Prévisionnels"
        ordering = ['-start_date', 'name']

    def __str__(self):
        return f"{self.name} - {self.allocated_amount} {self.currency} ({self.category.name})"


class Invoice(TenantModel):
    """
    Facture commerciale d'entreprise (Clients ou Fournisseurs) et Devis.
    """
    invoice_type = models.CharField(max_length=15, choices=INVOICE_TYPES, default='OUTGOING')
    invoice_number = models.CharField(max_length=100, help_text="Numéro officiel de facture (ex: FAC-2026-001)")
    partner_name = models.CharField(max_length=200, help_text="Nom du client ou fournisseur")
    partner_email = models.EmailField(blank=True, null=True)
    partner_phone = models.CharField(max_length=50, blank=True, null=True)
    partner_address = models.TextField(blank=True, null=True)
    partner_tax_id = models.CharField(max_length=100, blank=True, null=True, help_text="N° SIRET / NIF / TVA")
    
    issue_date = models.DateField()
    due_date = models.DateField()
    currency = models.CharField(max_length=10, choices=CURRENCY_CHOICES, default='EUR')
    status = models.CharField(max_length=15, choices=INVOICE_STATUS, default='DRAFT')
    
    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'), help_text="Taux de TVA en % (ex: 20.00)")
    tax_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    discount_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    total_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    paid_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    
    notes = models.TextField(blank=True, null=True, help_text="Notes ou mentions légales")
    terms = models.TextField(blank=True, null=True, help_text="Conditions de paiement")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = "Facture / Devis"
        verbose_name_plural = "Factures & Devis"
        ordering = ['-issue_date', '-created_at']

    def __str__(self):
        return f"{self.invoice_number} | {self.partner_name} | {self.total_amount} {self.currency} ({self.get_status_display()})"

    @property
    def remaining_due(self):
        return max(Decimal('0.00'), self.total_amount - self.paid_amount)


class InvoiceItem(TenantModel):
    """
    Ligne de facturation unitaire.
    """
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    description = models.CharField(max_length=255, help_text="Désignation du service ou produit")
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('1.00'))
    unit_price = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    total_price = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))

    class Meta:
        verbose_name = "Ligne de Facture"
        verbose_name_plural = "Lignes de Facture"

    def save(self, *args, **kwargs):
        self.total_price = Decimal(str(self.quantity)) * Decimal(str(self.unit_price))
        super().save(*args, **kwargs)


# ==============================================================================
# TONTINES & ÉPARGNE COLLECTIVE
# ==============================================================================

TONTINE_TYPES = (
    ('ROTATIVE', 'Tontine Rotative (Chacun son tour / Rangs)'),
    ('ACCUMULATIVE', 'Tontine Épargne & Accumulation (Cagnotte de fin)'),
    ('SOLIDARITY', 'Fonds de Secours & Caisse de Solidarité'),
)

TONTINE_FREQUENCIES = (
    ('WEEKLY', 'Hebdomadaire (Chaque semaine)'),
    ('BIWEEKLY', 'Bimensuelle (Toutes les 2 semaines)'),
    ('MONTHLY', 'Mensuelle (Chaque mois)'),
    ('QUARTERLY', 'Trimestrielle (Chaque trimestre)'),
)

TONTINE_STATUS = (
    ('DRAFT', 'En Préparation / Inscriptions'),
    ('ACTIVE', 'En Cours / Active'),
    ('COMPLETED', 'Terminée / Clôturée'),
    ('PAUSED', 'En Pause'),
)

MEMBER_STATUS = (
    ('ACTIVE', 'Actif'),
    ('SUSPENDED', 'Suspendu'),
    ('COMPLETED', 'A Terminé / A Ramassé'),
    ('EXITED', 'Retiré'),
)

ROUND_STATUS = (
    ('PENDING', 'À Venir / En Attente'),
    ('COLLECTING', 'Cotisations en cours'),
    ('COLLECTED', 'Cotisations Collectées'),
    ('PAID_OUT', 'Cagnotte Versée au Bénéficiaire'),
    ('CLOSED', 'Tour Clôturé'),
)

CONTRIBUTION_STATUS = (
    ('PAID', 'Payée / Validée'),
    ('PENDING', 'En Attente'),
    ('LATE', 'En Retard'),
)


class TontineGroup(TenantModel):
    """
    Groupe ou Cercle de Tontine / Épargne collective.
    """
    name = models.CharField(max_length=200, help_text="Nom du cercle (ex: Tontine des Cadres, Tontine Solidaire 2026)")
    tontine_type = models.CharField(max_length=20, choices=TONTINE_TYPES, default='ROTATIVE')
    contribution_amount = models.DecimalField(max_digits=14, decimal_places=2, help_text="Montant de la cotisation par part")
    currency = models.CharField(max_length=10, choices=CURRENCY_CHOICES, default='XOF')
    frequency = models.CharField(max_length=20, choices=TONTINE_FREQUENCIES, default='MONTHLY')
    start_date = models.DateField(help_text="Date de démarrage du 1er tour")
    end_date = models.DateField(blank=True, null=True, help_text="Date de fin estimée du cycle complet")
    status = models.CharField(max_length=20, choices=TONTINE_STATUS, default='DRAFT')
    
    account = models.ForeignKey(FinancialAccount, on_delete=models.SET_NULL, null=True, blank=True, related_name='tontines', help_text="Compte de trésorerie où transitent les fonds de la tontine")
    late_penalty_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), help_text="Pénalité forfaitaire en cas de retard de paiement")
    description = models.TextField(blank=True, null=True)
    rules = models.TextField(blank=True, null=True, help_text="Règlement intérieur et conditions d'attribution")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = "Cercle de Tontine"
        verbose_name_plural = "Cercles de Tontine"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.contribution_amount:,.2f} {self.currency} / {self.get_frequency_display()})"


class TontineMember(TenantModel):
    """
    Participant adhérent à une tontine.
    """
    tontine = models.ForeignKey(TontineGroup, on_delete=models.CASCADE, related_name='members')
    full_name = models.CharField(max_length=200, help_text="Nom complet du membre")
    phone = models.CharField(max_length=50, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    shares_count = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('1.00'), help_text="Nombre de parts souscrites (ex: 1.0, 2.0, 0.5)")
    payout_order = models.IntegerField(default=1, help_text="Ordre de ramassage / Rang du tour où ce membre perçoit la cagnotte")
    expected_payout_date = models.DateField(blank=True, null=True)
    has_received_payout = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=MEMBER_STATUS, default='ACTIVE')
    notes = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Membre de Tontine"
        verbose_name_plural = "Membres de Tontine"
        ordering = ['payout_order', 'full_name']

    def __str__(self):
        return f"Rang {self.payout_order}: {self.full_name} ({self.shares_count} part(s)) - {self.tontine.name}"


class TontineRound(TenantModel):
    """
    Session / Tour de ramassage de la tontine.
    """
    tontine = models.ForeignKey(TontineGroup, on_delete=models.CASCADE, related_name='rounds')
    round_number = models.IntegerField(help_text="Numéro du tour (ex: 1, 2, 3...)")
    due_date = models.DateField(help_text="Date d'échéance de versement des cotisations")
    beneficiary = models.ForeignKey(TontineMember, on_delete=models.SET_NULL, null=True, blank=True, related_name='beneficiary_rounds', help_text="Membre désigné pour remporter la cagnotte de ce tour")
    target_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'), help_text="Montant théorique total de la cagnotte")
    collected_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'), help_text="Montant réellement collecté auprès des membres")
    payout_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'), help_text="Montant net reversé au bénéficiaire")
    status = models.CharField(max_length=20, choices=ROUND_STATUS, default='PENDING')
    payout_date = models.DateField(blank=True, null=True, help_text="Date effective du versement de la cagnotte")
    notes = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Tour de Tontine"
        verbose_name_plural = "Tours de Tontine"
        ordering = ['round_number']
        unique_together = ('organization', 'tontine', 'round_number')

    def __str__(self):
        return f"{self.tontine.name} - Tour n°{self.round_number} ({self.due_date})"


class TontineContribution(TenantModel):
    """
    Cotisation unitaire payée par un membre pour un tour précis.
    """
    tontine = models.ForeignKey(TontineGroup, on_delete=models.CASCADE, related_name='contributions')
    round = models.ForeignKey(TontineRound, on_delete=models.CASCADE, related_name='contributions')
    member = models.ForeignKey(TontineMember, on_delete=models.CASCADE, related_name='contributions')
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    penalty_paid = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    payment_date = models.DateField()
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='CASH')
    reference = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=20, choices=CONTRIBUTION_STATUS, default='PAID')
    transaction = models.ForeignKey(Transaction, on_delete=models.SET_NULL, null=True, blank=True, related_name='tontine_contributions')

    class Meta:
        verbose_name = "Cotisation de Tontine"
        verbose_name_plural = "Cotisations de Tontine"
        ordering = ['-payment_date']
        unique_together = ('organization', 'round', 'member')

    def __str__(self):
        return f"{self.member.full_name} | Tour {self.round.round_number} | {self.amount} {self.tontine.currency}"


class TontinePayout(TenantModel):
    """
    Décaissement et versement de la cagnotte au bénéficiaire d'un tour.
    """
    tontine = models.ForeignKey(TontineGroup, on_delete=models.CASCADE, related_name='payouts')
    round = models.ForeignKey(TontineRound, on_delete=models.CASCADE, related_name='payouts')
    beneficiary = models.ForeignKey(TontineMember, on_delete=models.CASCADE, related_name='payouts')
    gross_amount = models.DecimalField(max_digits=14, decimal_places=2, help_text="Montant total brut de la cagnotte")
    deductions = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'), help_text="Retenues ou cotisations en avance déduites")
    net_amount = models.DecimalField(max_digits=14, decimal_places=2, help_text="Montant net remis au bénéficiaire")
    payout_date = models.DateField()
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='TRANSFER')
    reference = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    transaction = models.ForeignKey(Transaction, on_delete=models.SET_NULL, null=True, blank=True, related_name='tontine_payouts')

    class Meta:
        verbose_name = "Versement de Cagnotte"
        verbose_name_plural = "Versements de Cagnotte"
        ordering = ['-payout_date']

    def __str__(self):
        return f"Ramassage {self.beneficiary.full_name} | {self.net_amount} {self.tontine.currency} (Tour {self.round.round_number})"

