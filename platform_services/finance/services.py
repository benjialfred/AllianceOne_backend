import datetime
from decimal import Decimal
from django.db import transaction
from django.db.models import Sum, Q, F, Count
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import (
    FinancialAccount, FinancialCategory, Transaction, Budget,
    Invoice, InvoiceItem,
    TontineGroup, TontineMember, TontineRound,
    TontineContribution, TontinePayout
)


class FinanceService:
    @staticmethod
    @transaction.atomic
    def record_transaction(tenant, data, user=None):
        """
        Enregistre une transaction financière de manière atomique et met à jour
        les soldes des comptes concernés.
        """
        tx_type = data.get('transaction_type')
        account_id = data.get('account')
        dest_account_id = data.get('destination_account')
        amount = Decimal(str(data.get('amount', '0')))
        dest_amount = Decimal(str(data.get('destination_amount', amount))) if data.get('destination_amount') else amount
        status = data.get('status', 'COMPLETED')

        if amount <= Decimal('0'):
            raise ValidationError({'amount': 'Le montant doit être strictement supérieur à 0.'})

        try:
            account = FinancialAccount.objects.select_for_update().get(id=account_id, organization=tenant)
        except FinancialAccount.DoesNotExist:
            raise ValidationError({'account': 'Le compte spécifié est introuvable.'})

        dest_account = None
        if tx_type == 'TRANSFER':
            if not dest_account_id:
                raise ValidationError({'destination_account': 'Un compte destinataire est obligatoire pour un virement.'})
            if str(dest_account_id) == str(account_id):
                raise ValidationError({'destination_account': 'Le compte de destination doit être différent du compte source.'})
            try:
                dest_account = FinancialAccount.objects.select_for_update().get(id=dest_account_id, organization=tenant)
            except FinancialAccount.DoesNotExist:
                raise ValidationError({'destination_account': 'Le compte destinataire spécifié est introuvable.'})

        # Création de l'objet transaction
        tx = Transaction(
            organization=tenant,
            transaction_type=tx_type,
            title=data.get('title'),
            account=account,
            destination_account=dest_account,
            category_id=data.get('category') if tx_type != 'TRANSFER' else None,
            amount=amount,
            currency=account.currency,
            destination_amount=dest_amount if tx_type == 'TRANSFER' else None,
            exchange_rate=Decimal(str(data.get('exchange_rate', '1.0000'))),
            date=data.get('date', timezone.now().date()),
            reference_number=data.get('reference_number', ''),
            payment_method=data.get('payment_method', 'TRANSFER'),
            payee_payer=data.get('payee_payer', ''),
            status=status,
            notes=data.get('notes', ''),
            receipt_url=data.get('receipt_url', ''),
            is_reconciled=data.get('is_reconciled', False),
            recorded_by=user if user and user.is_authenticated else None
        )
        tx.save()

        # Si le statut est validé, on impacte immédiatement le solde
        if status == 'COMPLETED':
            FinanceService._apply_balance_impact(account, dest_account, tx_type, amount, dest_amount)

        return tx

    @staticmethod
    def _apply_balance_impact(account, dest_account, tx_type, amount, dest_amount):
        if tx_type == 'INCOME':
            account.current_balance += amount
            account.save(update_fields=['current_balance'])
        elif tx_type == 'EXPENSE':
            account.current_balance -= amount
            account.save(update_fields=['current_balance'])
        elif tx_type == 'TRANSFER':
            account.current_balance -= amount
            account.save(update_fields=['current_balance'])
            if dest_account:
                dest_account.current_balance += dest_amount
                dest_account.save(update_fields=['current_balance'])

    @staticmethod
    @transaction.atomic
    def rollback_transaction_impact(tx):
        """
        Annule l'impact d'une transaction sur les soldes de comptes.
        """
        if tx.status != 'COMPLETED':
            return

        account = FinancialAccount.objects.select_for_update().get(id=tx.account_id)
        if tx.transaction_type == 'INCOME':
            account.current_balance -= tx.amount
            account.save(update_fields=['current_balance'])
        elif tx.transaction_type == 'EXPENSE':
            account.current_balance += tx.amount
            account.save(update_fields=['current_balance'])
        elif tx.transaction_type == 'TRANSFER':
            account.current_balance += tx.amount
            account.save(update_fields=['current_balance'])
            if tx.destination_account_id:
                dest = FinancialAccount.objects.select_for_update().get(id=tx.destination_account_id)
                dest_amount = tx.destination_amount or tx.amount
                dest.current_balance -= dest_amount
                dest.save(update_fields=['current_balance'])

    @staticmethod
    @transaction.atomic
    def recalculate_account_balance(account):
        """
        Recalcule le solde exact du compte à partir de son solde initial
        et de toutes ses transactions terminées.
        """
        balance = account.initial_balance

        # Revenus directs
        incomes = Transaction.objects.filter(
            account=account,
            transaction_type='INCOME',
            status='COMPLETED'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        # Dépenses directes
        expenses = Transaction.objects.filter(
            account=account,
            transaction_type='EXPENSE',
            status='COMPLETED'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        # Virements sortants
        outgoing_transfers = Transaction.objects.filter(
            account=account,
            transaction_type='TRANSFER',
            status='COMPLETED'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        # Virements entrants
        incoming_transfers = Transaction.objects.filter(
            destination_account=account,
            transaction_type='TRANSFER',
            status='COMPLETED'
        ).aggregate(total=Sum('destination_amount'))['total'] or Decimal('0.00')

        account.current_balance = balance + incomes - expenses - outgoing_transfers + incoming_transfers
        account.save(update_fields=['current_balance'])
        return account.current_balance

    @staticmethod
    @transaction.atomic
    def record_invoice_payment(invoice, account_id, payment_amount, payment_method='TRANSFER', reference='', date=None, user=None):
        """
        Enregistre un paiement sur une facture et génère automatiquement la transaction financière liée.
        """
        payment_amount = Decimal(str(payment_amount))
        if payment_amount <= Decimal('0'):
            raise ValidationError({'amount': 'Le montant du paiement doit être supérieur à 0.'})

        remaining = invoice.total_amount - invoice.paid_amount
        if payment_amount > remaining:
            payment_amount = remaining

        invoice.paid_amount += payment_amount
        if invoice.paid_amount >= invoice.total_amount:
            invoice.status = 'PAID'
        else:
            invoice.status = 'PARTIAL'
        invoice.save(update_fields=['paid_amount', 'status'])

        # Déterminer le type de transaction
        tx_type = 'INCOME' if invoice.invoice_type in ['OUTGOING', 'QUOTATION'] else 'EXPENSE'
        title = f"Règlement facture {invoice.invoice_number} - {invoice.partner_name}"

        # Créer la transaction liée
        tx_data = {
            'transaction_type': tx_type,
            'title': title,
            'account': account_id,
            'amount': payment_amount,
            'date': date or timezone.now().date(),
            'reference_number': reference or f"PAY-{invoice.invoice_number}",
            'payment_method': payment_method,
            'payee_payer': invoice.partner_name,
            'status': 'COMPLETED',
            'notes': f"Paiement automatique enregistré pour la facture {invoice.invoice_number}",
        }

        return FinanceService.record_transaction(invoice.organization, tx_data, user=user)

    @staticmethod
    def generate_default_categories(tenant):
        """
        Initialise un plan de catégories financières standardisées pour les entreprises.
        """
        default_cats = [
            # Revenus
            {'name': 'Ventes de Prestations / Services', 'type': 'INCOME', 'color': '#10B981', 'icon': 'Briefcase', 'code': '706'},
            {'name': 'Vente de Marchandises / Produits', 'type': 'INCOME', 'color': '#059669', 'icon': 'Package', 'code': '707'},
            {'name': 'Revenus Financiers & Intérêts', 'type': 'INCOME', 'color': '#34D399', 'icon': 'TrendingUp', 'code': '760'},
            {'name': 'Subventions & Aides', 'type': 'INCOME', 'color': '#6EE7B7', 'icon': 'Award', 'code': '740'},
            {'name': 'Autres Produits d\'Exploitation', 'type': 'INCOME', 'color': '#A7F3D0', 'icon': 'PlusCircle', 'code': '758'},

            # Dépenses
            {'name': 'Salaires & Rémunérations', 'type': 'EXPENSE', 'color': '#EF4444', 'icon': 'Users', 'code': '641'},
            {'name': 'Charges Sociales & Patronales', 'type': 'EXPENSE', 'color': '#DC2626', 'icon': 'ShieldCheck', 'code': '645'},
            {'name': 'Loyer & Charges Locatives', 'type': 'EXPENSE', 'color': '#F97316', 'icon': 'Building', 'code': '613'},
            {'name': 'Achats Matières & Fournisseurs', 'type': 'EXPENSE', 'color': '#EA580C', 'icon': 'Truck', 'code': '601'},
            {'name': 'Logiciels, SaaS & Abonnements', 'type': 'EXPENSE', 'color': '#8B5CF6', 'icon': 'Laptop', 'code': '618'},
            {'name': 'Marketing, Publicité & Communication', 'type': 'EXPENSE', 'color': '#EC4899', 'icon': 'Megaphone', 'code': '623'},
            {'name': 'Frais de Déplacement & Missions', 'type': 'EXPENSE', 'color': '#F59E0B', 'icon': 'Navigation', 'code': '625'},
            {'name': 'Services Bancaires & Commissions', 'type': 'EXPENSE', 'color': '#64748B', 'icon': 'CreditCard', 'code': '627'},
            {'name': 'Impôts, Taxes & Cotisations', 'type': 'EXPENSE', 'color': '#B91C1C', 'icon': 'FileText', 'code': '635'},
            {'name': 'Électricité, Eau & Télécoms', 'type': 'EXPENSE', 'color': '#0284C7', 'icon': 'Zap', 'code': '606'},
            {'name': 'Honoraires (Comptable, Avocat)', 'type': 'EXPENSE', 'color': '#7C3AED', 'icon': 'UserCheck', 'code': '622'},
        ]

        created = []
        for cat in default_cats:
            obj, _ = FinancialCategory.objects.get_or_create(
                organization=tenant,
                name=cat['name'],
                category_type=cat['type'],
                defaults={
                    'color': cat['color'],
                    'icon': cat['icon'],
                    'code': cat['code'],
                    'description': f"Catégorie standard {cat['name']}"
                }
            )
            created.append(obj)
        return created

    @staticmethod
    def get_dashboard_analytics(tenant, currency_filter=None):
        """
        Calcule les KPIs temps-réel, graphiques de flux de trésorerie,
        répartition par devise et alertes intelligentes.
        """
        today = timezone.now().date()
        first_day_this_month = today.replace(day=1)
        
        # Filtre sur devise optionnel
        tx_qs = Transaction.objects.filter(organization=tenant, status='COMPLETED')
        acc_qs = FinancialAccount.objects.filter(organization=tenant, is_active=True)
        inv_qs = Invoice.objects.filter(organization=tenant)

        if currency_filter and currency_filter != 'ALL':
            tx_qs = tx_qs.filter(currency=currency_filter)
            acc_qs = acc_qs.filter(currency=currency_filter)
            inv_qs = inv_qs.filter(currency=currency_filter)

        # 1. Soldes par devise
        currencies_summary = []
        for c_code, c_label in [('EUR', 'EUR (€)'), ('USD', 'USD ($)'), ('XOF', 'XOF (F.CFA)'), ('GBP', 'GBP (£)'), ('CAD', 'CAD ($ CA)'), ('CHF', 'CHF (CHF)')]:
            cur_accounts = FinancialAccount.objects.filter(organization=tenant, currency=c_code, is_active=True)
            total_bal = cur_accounts.aggregate(tot=Sum('current_balance'))['tot'] or Decimal('0.00')
            count = cur_accounts.count()
            if count > 0 or total_bal != Decimal('0.00'):
                currencies_summary.append({
                    'currency': c_code,
                    'label': c_label,
                    'total_balance': float(total_bal),
                    'accounts_count': count
                })

        # 2. Total Revenus & Dépenses du mois en cours
        this_month_incomes = tx_qs.filter(
            transaction_type='INCOME',
            date__gte=first_day_this_month
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        this_month_expenses = tx_qs.filter(
            transaction_type='EXPENSE',
            date__gte=first_day_this_month
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        net_profit = this_month_incomes - this_month_expenses

        # 3. Flux mensuel (6 derniers mois)
        cashflow_timeline = []
        for i in range(5, -1, -1):
            # Calcul du premier et dernier jour du mois i
            m_year = today.year
            m_month = today.month - i
            while m_month <= 0:
                m_month += 12
                m_year -= 1
            
            start_m = datetime.date(m_year, m_month, 1)
            if m_month == 12:
                end_m = datetime.date(m_year + 1, 1, 1) - datetime.timedelta(days=1)
            else:
                end_m = datetime.date(m_year, m_month + 1, 1) - datetime.timedelta(days=1)

            month_in = tx_qs.filter(
                transaction_type='INCOME',
                date__range=[start_m, end_m]
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

            month_out = tx_qs.filter(
                transaction_type='EXPENSE',
                date__range=[start_m, end_m]
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

            cashflow_timeline.append({
                'month_name': start_m.strftime('%b %Y'),
                'period_key': start_m.strftime('%Y-%m'),
                'income': float(month_in),
                'expense': float(month_out),
                'net': float(month_in - month_out)
            })

        # 4. Répartition des dépenses par catégorie (Mois en cours ou global)
        category_breakdown = []
        cat_stats = tx_qs.filter(
            transaction_type='EXPENSE',
            date__gte=first_day_this_month
        ).values('category__id', 'category__name', 'category__color', 'category__icon').annotate(
            total_spent=Sum('amount'),
            tx_count=Count('id')
        ).order_by('-total_spent')[:8]

        total_cat_expenses = sum([c['total_spent'] for c in cat_stats]) or Decimal('1.00')
        for c in cat_stats:
            cat_name = c['category__name'] or 'Non Catégorisé'
            cat_color = c['category__color'] or '#94A3B8'
            cat_icon = c['category__icon'] or 'Folder'
            spent = c['total_spent'] or Decimal('0.00')
            pct = round(float((spent / total_cat_expenses) * 100), 1) if this_month_expenses > 0 else 0
            category_breakdown.append({
                'id': str(c['category__id']) if c['category__id'] else None,
                'name': cat_name,
                'color': cat_color,
                'icon': cat_icon,
                'total_spent': float(spent),
                'percentage': pct,
                'count': c['tx_count']
            })

        # 5. Budgets en cours & Alertes de dépassement
        budgets_data = []
        active_budgets = Budget.objects.filter(organization=tenant, is_active=True).select_related('category')
        alerts = []

        for b in active_budgets:
            # Calcul des dépenses réelles dans la période du budget
            spent = Transaction.objects.filter(
                organization=tenant,
                category=b.category,
                transaction_type='EXPENSE',
                status='COMPLETED',
                date__range=[b.start_date, b.end_date]
            ).aggregate(tot=Sum('amount'))['tot'] or Decimal('0.00')

            pct_used = round(float((spent / b.allocated_amount) * 100), 1) if b.allocated_amount > 0 else 0
            remaining = max(Decimal('0.00'), b.allocated_amount - spent)
            
            is_exceeded = spent > b.allocated_amount
            is_warning = pct_used >= b.alert_threshold_percentage

            if is_exceeded:
                alerts.append({
                    'type': 'DANGER',
                    'title': f'Dépassement de budget : {b.name}',
                    'message': f'Le budget alloué de {b.allocated_amount:,.2f} {b.currency} est dépassé de {(spent - b.allocated_amount):,.2f} {b.currency} ({pct_used}%).',
                    'link': '/finance/budgets'
                })
            elif is_warning:
                alerts.append({
                    'type': 'WARNING',
                    'title': f'Seuil d\'alerte budget : {b.name}',
                    'message': f'{pct_used}% du budget consommé ({spent:,.2f} / {b.allocated_amount:,.2f} {b.currency}).',
                    'link': '/finance/budgets'
                })

            budgets_data.append({
                'id': str(b.id),
                'name': b.name,
                'category_name': b.category.name,
                'allocated': float(b.allocated_amount),
                'spent': float(spent),
                'remaining': float(remaining),
                'percentage': pct_used,
                'currency': b.currency,
                'is_warning': is_warning,
                'is_exceeded': is_exceeded,
            })

        # 6. Factures impayées & Alertes
        unpaid_invoices_count = inv_qs.filter(status__in=['SENT', 'PARTIAL', 'OVERDUE']).count()
        overdue_invoices_count = inv_qs.filter(status='OVERDUE').count()
        unpaid_invoices_sum = inv_qs.filter(status__in=['SENT', 'PARTIAL', 'OVERDUE']).aggregate(
            tot=Sum(F('total_amount') - F('paid_amount'))
        )['tot'] or Decimal('0.00')

        if overdue_invoices_count > 0:
            alerts.append({
                'type': 'WARNING',
                'title': f'{overdue_invoices_count} Facture(s) en retard de paiement',
                'message': f'Total impayé en retard nécessitant une relance client.',
                'link': '/finance/invoices'
            })

        # 7. Alertes de solde négatif
        for acc in FinancialAccount.objects.filter(organization=tenant, is_active=True):
            if acc.current_balance < Decimal('0.00'):
                alerts.append({
                    'type': 'DANGER',
                    'title': f'Solde négatif sur {acc.name}',
                    'message': f'Le compte présente un découvert de {acc.current_balance:,.2f} {acc.currency}.',
                    'link': '/finance/accounts'
                })

        return {
            'summary': {
                'this_month_income': float(this_month_incomes),
                'this_month_expense': float(this_month_expenses),
                'net_profit': float(net_profit),
                'currencies': currencies_summary,
                'unpaid_invoices_sum': float(unpaid_invoices_sum),
                'unpaid_invoices_count': unpaid_invoices_count,
                'overdue_invoices_count': overdue_invoices_count,
            },
            'cashflow_timeline': cashflow_timeline,
            'category_breakdown': category_breakdown,
            'budgets': budgets_data[:5],
            'alerts': alerts
        }

    # ==========================================================================
    # TONTINE DOMAIN LOGIC
    # ==========================================================================

    @staticmethod
    @transaction.atomic
    def generate_tontine_rounds(tontine):
        """
        Génère automatiquement les tours/sessions d'une tontine en fonction
        des membres actifs et de leur ordre de passage (payout_order).
        """
        members = tontine.members.filter(status='ACTIVE').order_by('payout_order', 'created_at')
        if not members.exists():
            raise ValidationError({'members': 'La tontine doit avoir au moins un membre actif pour générer les tours.'})

        # Supprimer les tours existants non commencés
        tontine.rounds.filter(status='PENDING').delete()

        current_date = tontine.start_date
        total_shares = sum([m.shares_count for m in members])
        target_pot = tontine.contribution_amount * total_shares

        # Calcul de l'intervalle selon la fréquence
        interval_days = 30
        if tontine.frequency == 'WEEKLY':
            interval_days = 7
        elif tontine.frequency == 'BIWEEKLY':
            interval_days = 14
        elif tontine.frequency == 'MONTHLY':
            interval_days = 30
        elif tontine.frequency == 'QUARTERLY':
            interval_days = 90

        rounds = []
        for idx, member in enumerate(members, start=1):
            due = current_date + datetime.timedelta(days=(idx - 1) * interval_days)
            round_obj = TontineRound.objects.create(
                organization=tontine.organization,
                tontine=tontine,
                round_number=idx,
                due_date=due,
                beneficiary=member,
                target_amount=target_pot,
                collected_amount=Decimal('0.00'),
                payout_amount=Decimal('0.00'),
                status='COLLECTING' if idx == 1 else 'PENDING'
            )
            rounds.append(round_obj)
            member.expected_payout_date = due
            member.save(update_fields=['expected_payout_date'])

        tontine.status = 'ACTIVE'
        tontine.save(update_fields=['status'])
        return rounds

    @staticmethod
    @transaction.atomic
    def record_tontine_contribution(tenant, data, user=None):
        """
        Enregistre la cotisation d'un membre pour un tour, met à jour le montant
        collecté et génère la transaction de trésorerie si un compte est configuré.
        """
        tontine_id = data.get('tontine')
        round_id = data.get('round')
        member_id = data.get('member')
        amount = Decimal(str(data.get('amount', '0')))
        penalty_paid = Decimal(str(data.get('penalty_paid', '0.00')))
        payment_date = data.get('payment_date', timezone.now().date())
        payment_method = data.get('payment_method', 'CASH')
        reference = data.get('reference', '')

        if amount <= Decimal('0'):
            raise ValidationError({'amount': 'Le montant de la cotisation doit être supérieur à 0.'})

        tontine = TontineGroup.objects.get(id=tontine_id, organization=tenant)
        round_obj = TontineRound.objects.select_for_update().get(id=round_id, tontine=tontine)
        member = TontineMember.objects.get(id=member_id, tontine=tontine)

        # Créer la transaction financière sur le compte de trésorerie lié
        tx = None
        if tontine.account:
            tx_data = {
                'transaction_type': 'INCOME',
                'title': f"Cotisation Tontine '{tontine.name}' - {member.full_name} (Tour {round_obj.round_number})",
                'account': tontine.account_id,
                'amount': amount + penalty_paid,
                'currency': tontine.currency,
                'date': payment_date,
                'payment_method': payment_method,
                'reference_number': reference or f"TONT-COT-{round_obj.round_number}-{member.id.hex[:4].upper()}",
                'payee_payer': member.full_name,
                'status': 'COMPLETED',
                'notes': f"Cotisation Tontine Tour #{round_obj.round_number}",
            }
            tx = FinanceService.record_transaction(tenant, tx_data, user=user)

        contribution = TontineContribution.objects.create(
            organization=tenant,
            tontine=tontine,
            round=round_obj,
            member=member,
            amount=amount,
            penalty_paid=penalty_paid,
            payment_date=payment_date,
            payment_method=payment_method,
            reference=reference,
            status='PAID',
            transaction=tx
        )

        # Mettre à jour le montant collecté sur le tour
        round_obj.collected_amount += amount
        if round_obj.collected_amount >= round_obj.target_amount and round_obj.status != 'PAID_OUT':
            round_obj.status = 'COLLECTED'
        round_obj.save(update_fields=['collected_amount', 'status'])

        return contribution

    @staticmethod
    @transaction.atomic
    def record_tontine_payout(tenant, data, user=None):
        """
        Enregistre le ramassage / versement de la cagnotte au bénéficiaire,
        met à jour le statut du tour et génère la sortie de trésorerie liée.
        """
        tontine_id = data.get('tontine')
        round_id = data.get('round')
        beneficiary_id = data.get('beneficiary')
        gross_amount = Decimal(str(data.get('gross_amount', '0')))
        deductions = Decimal(str(data.get('deductions', '0.00')))
        net_amount = gross_amount - deductions
        payout_date = data.get('payout_date', timezone.now().date())
        payment_method = data.get('payment_method', 'TRANSFER')
        reference = data.get('reference', '')
        notes = data.get('notes', '')

        if net_amount <= Decimal('0'):
            raise ValidationError({'net_amount': 'Le montant net versé doit être supérieur à 0.'})

        tontine = TontineGroup.objects.get(id=tontine_id, organization=tenant)
        round_obj = TontineRound.objects.select_for_update().get(id=round_id, tontine=tontine)
        beneficiary = TontineMember.objects.select_for_update().get(id=beneficiary_id, tontine=tontine)

        # Créer la transaction de sortie de trésorerie
        tx = None
        if tontine.account:
            tx_data = {
                'transaction_type': 'EXPENSE',
                'title': f"Ramassage Cagnotte Tontine '{tontine.name}' - {beneficiary.full_name} (Tour {round_obj.round_number})",
                'account': tontine.account_id,
                'amount': net_amount,
                'currency': tontine.currency,
                'date': payout_date,
                'payment_method': payment_method,
                'reference_number': reference or f"TONT-RAM-{round_obj.round_number}-{beneficiary.id.hex[:4].upper()}",
                'payee_payer': beneficiary.full_name,
                'status': 'COMPLETED',
                'notes': notes or f"Versement de la cagnotte du Tour #{round_obj.round_number}",
            }
            tx = FinanceService.record_transaction(tenant, tx_data, user=user)

        payout = TontinePayout.objects.create(
            organization=tenant,
            tontine=tontine,
            round=round_obj,
            beneficiary=beneficiary,
            gross_amount=gross_amount,
            deductions=deductions,
            net_amount=net_amount,
            payout_date=payout_date,
            payment_method=payment_method,
            reference=reference,
            notes=notes,
            transaction=tx
        )

        round_obj.payout_amount = net_amount
        round_obj.payout_date = payout_date
        round_obj.status = 'PAID_OUT'
        round_obj.save(update_fields=['payout_amount', 'payout_date', 'status'])

        beneficiary.has_received_payout = True
        beneficiary.status = 'COMPLETED'
        beneficiary.save(update_fields=['has_received_payout', 'status'])

        # Passer le tour suivant en 'COLLECTING'
        next_round = tontine.rounds.filter(round_number=round_obj.round_number + 1).first()
        if next_round:
            next_round.status = 'COLLECTING'
            next_round.save(update_fields=['status'])
        else:
            # Plus de tours : tontine complétée
            tontine.status = 'COMPLETED'
            tontine.save(update_fields=['status'])

        return payout

