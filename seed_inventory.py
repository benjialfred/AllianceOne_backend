import os
import django
from decimal import Decimal
import random

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'alliance_platform.settings')
django.setup()

from platform_services.identity.models import Organization
from platform_services.inventory.models import (
    Category, Unit, Warehouse, WarehouseLocation,
    Product, ProductStock, Supplier,
    PurchaseOrder, PurchaseOrderItem,
    StockMovement, InventoryAudit, InventoryAuditItem
)
from platform_services.inventory.services import InventoryService

def seed_inventory():
    print("[*] Demarrage du peuplement du module Gestion des Stocks & Logistique...")
    
    # Recuperer l'organisation par defaut
    org = Organization.objects.first()
    if not org:
        org = Organization.objects.create(name="Alliance One Default")
        print(f"[+] Organisation creee : {org.name}")
    else:
        print(f"[+] Organisation active : {org.name}")

    # 1. Unités de mesure
    units_data = [
        {"name": "Unité", "symbol": "U", "description": "Pièce unitaire"},
        {"name": "Carton (x24)", "symbol": "ctn", "description": "Conditionnement carton de 24"},
        {"name": "Kilogramme", "symbol": "kg", "description": "Poids en kilogrammes"},
        {"name": "Litre", "symbol": "L", "description": "Volume en litres"},
        {"name": "Paquet (x100)", "symbol": "pqt", "description": "Paquet de 100 unités"},
        {"name": "Rouleau", "symbol": "rlx", "description": "Rouleau standard"},
    ]
    units = {}
    for u in units_data:
        unit, _ = Unit.objects.get_or_create(
            organization=org,
            symbol=u["symbol"],
            defaults={"name": u["name"], "description": u["description"]}
        )
        units[u["symbol"]] = unit
    print(f"[+] {len(units)} Unites creees ou verifiees.")

    # 2. Catégories d'articles
    cats_data = [
        {"name": "Matériel Informatique & Électronique", "code": "IT-ELEC", "description": "PC, écrans, périphériques, serveurs"},
        {"name": "Fournitures de Bureau & Papeterie", "code": "BUREAU", "description": "Cahiers, stylos, papier A4, classeurs"},
        {"name": "Mobilier & Équipement", "code": "MOBILIER", "description": "Bureaux, chaises ergonomiques, tableaux"},
        {"name": "Outillage & Maintenance", "code": "MAINT", "description": "Câblage, pièces de rechange, maintenance"},
        {"name": "Consommables & Entretien", "code": "CONSO", "description": "Produits d'hygiène, désinfectants, éponges"},
    ]
    categories = {}
    for c in cats_data:
        cat, _ = Category.objects.get_or_create(
            organization=org,
            code=c["code"],
            defaults={"name": c["name"], "description": c["description"]}
        )
        categories[c["code"]] = cat
    print(f"[+] {len(categories)} Categories creees.")

    # 3. Entrepôts & Dépôts
    wh_data = [
        {"code": "DEP-CENTRAL", "name": "Entrepôt Principal Central", "address": "Zone Industrielle Nord, Bât. A", "city": "Douala", "manager_name": "Alain Mbarga", "phone": "+237 670 11 22 33", "is_default": True, "capacity_m3": Decimal("1500.00")},
        {"code": "DEP-LOG-02", "name": "Dépôt Secondaire Ouest", "address": "Avenue Commerciale 45", "city": "Yaoundé", "manager_name": "Christelle Ngo", "phone": "+237 699 44 55 66", "is_default": False, "capacity_m3": Decimal("600.00")},
        {"code": "MAG-VENTE", "name": "Magasin & Comptoir de Vente", "address": "Centre-ville Plaza, Rez-de-chaussée", "city": "Douala", "manager_name": "Marc Ondoa", "phone": "+237 655 77 88 99", "is_default": False, "capacity_m3": Decimal("200.00")},
    ]
    warehouses = {}
    for w in wh_data:
        wh, _ = Warehouse.objects.get_or_create(
            organization=org,
            code=w["code"],
            defaults={
                "name": w["name"], "address": w["address"], "city": w["city"],
                "manager_name": w["manager_name"], "phone": w["phone"],
                "is_default": w["is_default"], "capacity_m3": w["capacity_m3"]
            }
        )
        warehouses[w["code"]] = wh

        # Create sample locations
        for zone in ["A", "B"]:
            for aisle in ["01", "02"]:
                WarehouseLocation.objects.get_or_create(
                    organization=org,
                    warehouse=wh,
                    code=f"{zone}-{aisle}",
                    defaults={"zone": f"Zone {zone}", "aisle": f"Allée {aisle}"}
                )
    print(f"[+] {len(warehouses)} Entrepots configures avec leurs emplacements.")

    # 4. Fournisseurs
    suppliers_data = [
        {"code": "FOURN-TECH", "name": "TechGlobal Distribution S.A.", "contact_name": "Jean-Pierre Vaneck", "email": "contact@techglobal.com", "phone": "+237 671 00 11 22", "city": "Douala", "payment_terms": "30 jours fin de mois", "tax_id": "M01928374A"},
        {"code": "FOURN-PAP", "name": "Papeterie Centrale & Bureautique", "contact_name": "Sophie Ewane", "email": "commandes@papeterie-centrale.cm", "phone": "+237 690 33 44 55", "city": "Yaoundé", "payment_terms": "Comptant à la livraison", "tax_id": "M08374619B"},
        {"code": "FOURN-MOB", "name": "Mobilier & Confort Pro", "contact_name": "David Kamga", "email": "sales@mobilierconfort.com", "phone": "+237 650 66 77 88", "city": "Douala", "payment_terms": "45 jours", "tax_id": "M05544332C"},
    ]
    suppliers = {}
    for s in suppliers_data:
        sup, _ = Supplier.objects.get_or_create(
            organization=org,
            code=s["code"],
            defaults={
                "name": s["name"], "contact_name": s["contact_name"],
                "email": s["email"], "phone": s["phone"], "city": s["city"],
                "payment_terms": s["payment_terms"], "tax_id": s["tax_id"], "rating": 5
            }
        )
        suppliers[s["code"]] = sup
    print(f"[+] {len(suppliers)} Fournisseurs enregistres.")

    # 5. Articles du catalogue
    products_data = [
        {
            "sku": "INF-LAP-001",
            "barcode": "3760123450011",
            "name": "Ordinateur Portable ProBook 15.6'' Core i7 16GB",
            "description": "PC portable professionnel ultra-rapide avec écran Full HD et SSD 512GB",
            "category": categories["IT-ELEC"],
            "unit": units["U"],
            "purchase_price": Decimal("450000.00"),
            "selling_price": Decimal("590000.00"),
            "min_stock_level": Decimal("4.00"),
            "max_stock_level": Decimal("25.00"),
            "reorder_quantity": Decimal("10.00"),
            "initial_stocks": {"DEP-CENTRAL": Decimal("12.00"), "DEP-LOG-02": Decimal("3.00"), "MAG-VENTE": Decimal("2.00")},
            "image_url": "https://images.unsplash.com/photo-1496181133206-80ce9b88a853?w=500&auto=format&fit=crop&q=60"
        },
        {
            "sku": "INF-ECR-002",
            "barcode": "3760123450028",
            "name": "Écran 27'' IPS 4K Ultra-Clair",
            "description": "Moniteur haute résolution ergonomique avec port USB-C",
            "category": categories["IT-ELEC"],
            "unit": units["U"],
            "purchase_price": Decimal("140000.00"),
            "selling_price": Decimal("195000.00"),
            "min_stock_level": Decimal("5.00"),
            "max_stock_level": Decimal("40.00"),
            "reorder_quantity": Decimal("15.00"),
            "initial_stocks": {"DEP-CENTRAL": Decimal("18.00"), "MAG-VENTE": Decimal("4.00")},
            "image_url": "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=500&auto=format&fit=crop&q=60"
        },
        {
            "sku": "INF-IMP-003",
            "barcode": "3760123450035",
            "name": "Imprimante Multifonction Laser Couleur Réseau",
            "description": "Imprimante recto-verso automatique avec scanner haute cadence",
            "category": categories["IT-ELEC"],
            "unit": units["U"],
            "purchase_price": Decimal("220000.00"),
            "selling_price": Decimal("295000.00"),
            "min_stock_level": Decimal("2.00"),
            "max_stock_level": Decimal("10.00"),
            "reorder_quantity": Decimal("5.00"),
            "initial_stocks": {"DEP-CENTRAL": Decimal("1.00"), "MAG-VENTE": Decimal("0.00")}, # Low stock
            "image_url": "https://images.unsplash.com/photo-1612815154858-60aa4c59eaa6?w=500&auto=format&fit=crop&q=60"
        },
        {
            "sku": "PAP-RAM-010",
            "barcode": "3760123450103",
            "name": "Carton de Rames Papier A4 80g (5x500 f.)",
            "description": "Papier blanc supérieur pour impressions laser et jet d'encre haute qualité",
            "category": categories["BUREAU"],
            "unit": units["ctn"],
            "purchase_price": Decimal("18500.00"),
            "selling_price": Decimal("24500.00"),
            "min_stock_level": Decimal("20.00"),
            "max_stock_level": Decimal("200.00"),
            "reorder_quantity": Decimal("50.00"),
            "initial_stocks": {"DEP-CENTRAL": Decimal("120.00"), "DEP-LOG-02": Decimal("45.00"), "MAG-VENTE": Decimal("15.00")},
            "image_url": "https://images.unsplash.com/photo-1589330694653-ded6df03f754?w=500&auto=format&fit=crop&q=60"
        },
        {
            "sku": "PAP-STY-011",
            "barcode": "3760123450110",
            "name": "Boîte de 50 Stylos à bille Bleu Haute Précision",
            "description": "Pointe fine 0.7mm encre fluide longue durée",
            "category": categories["BUREAU"],
            "unit": units["pqt"],
            "purchase_price": Decimal("7500.00"),
            "selling_price": Decimal("11500.00"),
            "min_stock_level": Decimal("15.00"),
            "max_stock_level": Decimal("150.00"),
            "reorder_quantity": Decimal("40.00"),
            "initial_stocks": {"DEP-CENTRAL": Decimal("8.00"), "MAG-VENTE": Decimal("2.00")}, # Critical low stock!
            "image_url": "https://images.unsplash.com/photo-1585336261026-77cc7c39299f?w=500&auto=format&fit=crop&q=60"
        },
        {
            "sku": "MOB-CHAIR-020",
            "barcode": "3760123450202",
            "name": "Fauteuil de Bureau Ergonomique Mesh Pro",
            "description": "Soutien lombaire réglable, accoudoirs 3D et mécanisme synchrone",
            "category": categories["MOBILIER"],
            "unit": units["U"],
            "purchase_price": Decimal("85000.00"),
            "selling_price": Decimal("130000.00"),
            "min_stock_level": Decimal("6.00"),
            "max_stock_level": Decimal("50.00"),
            "reorder_quantity": Decimal("15.00"),
            "initial_stocks": {"DEP-CENTRAL": Decimal("22.00"), "MAG-VENTE": Decimal("5.00")},
            "image_url": "https://images.unsplash.com/photo-1580481077195-c266854bcf93?w=500&auto=format&fit=crop&q=60"
        },
        {
            "sku": "MOB-DESK-021",
            "barcode": "3760123450219",
            "name": "Bureau Électrique Assis-Debout 160x80cm",
            "description": "Double moteur silencieux avec mémorisation de 4 hauteurs",
            "category": categories["MOBILIER"],
            "unit": units["U"],
            "purchase_price": Decimal("210000.00"),
            "selling_price": Decimal("315000.00"),
            "min_stock_level": Decimal("3.00"),
            "max_stock_level": Decimal("20.00"),
            "reorder_quantity": Decimal("8.00"),
            "initial_stocks": {"DEP-CENTRAL": Decimal("0.00")}, # RUPTURE TOTALE !
            "image_url": "https://images.unsplash.com/photo-1518455027359-f3f8164ba6bd?w=500&auto=format&fit=crop&q=60"
        },
        {
            "sku": "MNT-CAB-030",
            "barcode": "3760123450301",
            "name": "Bobine Câble Réseau Cat6a SFTP 305m",
            "description": "Câble cuivre haute performance blindé pour baies de brassage et postes",
            "category": categories["MAINT"],
            "unit": units["rlx"],
            "purchase_price": Decimal("95000.00"),
            "selling_price": Decimal("135000.00"),
            "min_stock_level": Decimal("5.00"),
            "max_stock_level": Decimal("30.00"),
            "reorder_quantity": Decimal("10.00"),
            "initial_stocks": {"DEP-CENTRAL": Decimal("14.00"), "DEP-LOG-02": Decimal("4.00")},
            "image_url": "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=500&auto=format&fit=crop&q=60"
        },
        {
            "sku": "MNT-OND-031",
            "barcode": "3760123450318",
            "name": "Onduleur Ligne Interactive 1500VA / 900W",
            "description": "Protection parafoudre et régulation automatique de tension AVR avec écran LCD",
            "category": categories["MAINT"],
            "unit": units["U"],
            "purchase_price": Decimal("115000.00"),
            "selling_price": Decimal("165000.00"),
            "min_stock_level": Decimal("4.00"),
            "max_stock_level": Decimal("25.00"),
            "reorder_quantity": Decimal("8.00"),
            "initial_stocks": {"DEP-CENTRAL": Decimal("9.00"), "MAG-VENTE": Decimal("3.00")},
            "image_url": "https://images.unsplash.com/photo-1550751827-4bd374c3f58b?w=500&auto=format&fit=crop&q=60"
        },
        {
            "sku": "HYG-GEL-040",
            "barcode": "3760123450400",
            "name": "Bidon Gel Hydroalcoolique 5L Norme EN14476",
            "description": "Désinfection rapide des mains sans rinçage pour distributeurs muraux",
            "category": categories["CONSO"],
            "unit": units["L"],
            "purchase_price": Decimal("8500.00"),
            "selling_price": Decimal("13000.00"),
            "min_stock_level": Decimal("10.00"),
            "max_stock_level": Decimal("80.00"),
            "reorder_quantity": Decimal("25.00"),
            "initial_stocks": {"DEP-CENTRAL": Decimal("35.00"), "DEP-LOG-02": Decimal("12.00"), "MAG-VENTE": Decimal("8.00")},
            "image_url": "https://images.unsplash.com/photo-1584744982491-665216d95f8b?w=500&auto=format&fit=crop&q=60"
        }
    ]

    created_products = []
    for p_info in products_data:
        prod, _ = Product.objects.get_or_create(
            organization=org,
            sku=p_info["sku"],
            defaults={
                "barcode": p_info["barcode"],
                "name": p_info["name"],
                "description": p_info["description"],
                "category": p_info["category"],
                "unit": p_info["unit"],
                "purchase_price": p_info["purchase_price"],
                "selling_price": p_info["selling_price"],
                "min_stock_level": p_info["min_stock_level"],
                "max_stock_level": p_info["max_stock_level"],
                "reorder_quantity": p_info["reorder_quantity"],
                "image_url": p_info["image_url"],
            }
        )
        created_products.append(prod)

        # Peuplement des stocks et mouvements initiaux
        for wh_code, qty in p_info["initial_stocks"].items():
            wh = warehouses[wh_code]
            stock_obj, is_new = ProductStock.objects.get_or_create(
                organization=org,
                product=prod,
                warehouse=wh,
                defaults={
                    "quantity_on_hand": qty,
                    "pmp_cost": prod.purchase_price
                }
            )
            if is_new and qty > Decimal("0.00"):
                StockMovement.objects.create(
                    organization=org,
                    product=prod,
                    target_warehouse=wh,
                    movement_type='ENTREE_RECEPTION',
                    quantity=qty,
                    unit_cost=prod.purchase_price,
                    total_cost=qty * prod.purchase_price,
                    reference_document="STOCK-INITIAL-2026",
                    reason="Initialisation du stock de démarrage"
                )

    print(f"[+] {len(created_products)} Articles catalogues et valorises dans les entrepots.")

    # 6. Bons de Commande Fournisseur (Purchase Orders)
    tech_sup = suppliers["FOURN-TECH"]
    central_wh = warehouses["DEP-CENTRAL"]

    po1, _ = PurchaseOrder.objects.get_or_create(
        organization=org,
        order_number="BC-2026-001",
        defaults={
            "supplier": tech_sup,
            "warehouse": central_wh,
            "status": "COMMANDE",
            "expected_delivery_date": "2026-08-25",
            "notes": "Commande de réapprovisionnement matériel informatique et moniteurs.",
            "total_ht": Decimal("4850000.00"),
            "total_tax": Decimal("933625.00"),
            "total_ttc": Decimal("5783625.00")
        }
    )
    if po1.items.count() == 0:
        PurchaseOrderItem.objects.create(
            organization=org, purchase_order=po1, product=created_products[0],
            ordered_quantity=Decimal("8.00"), unit_price=Decimal("450000.00"),
            tax_rate=Decimal("19.25"), total_price=Decimal("3600000.00")
        )
        PurchaseOrderItem.objects.create(
            organization=org, purchase_order=po1, product=created_products[1],
            ordered_quantity=Decimal("10.00"), unit_price=Decimal("125000.00"),
            tax_rate=Decimal("19.25"), total_price=Decimal("1250000.00")
        )

    mob_sup = suppliers["FOURN-MOB"]
    po2, _ = PurchaseOrder.objects.get_or_create(
        organization=org,
        order_number="BC-2026-002",
        defaults={
            "supplier": mob_sup,
            "warehouse": central_wh,
            "status": "RECU_TOTAL",
            "expected_delivery_date": "2026-08-10",
            "notes": "Mobilier de bureau pour nouvel open-space.",
            "total_ht": Decimal("2550000.00"),
            "total_tax": Decimal("490875.00"),
            "total_ttc": Decimal("3040875.00")
        }
    )
    if po2.items.count() == 0:
        PurchaseOrderItem.objects.create(
            organization=org, purchase_order=po2, product=created_products[5], # Fauteuils
            ordered_quantity=Decimal("30.00"), received_quantity=Decimal("30.00"),
            unit_price=Decimal("85000.00"), tax_rate=Decimal("19.25"),
            total_price=Decimal("2550000.00")
        )

    print("[+] Bons de commande fournisseurs d'exemple crees.")

    # 7. Session d'Inventaire Physique Exemple
    audit, _ = InventoryAudit.objects.get_or_create(
        organization=org,
        audit_number="INV-2026-T3",
        defaults={
            "title": "Inventaire Trimestriel Q3 - Dépôt Central",
            "warehouse": central_wh,
            "status": "EN_COURS",
            "scheduled_date": "2026-08-15",
            "responsible_name": "Alain Mbarga",
            "notes": "Comptage tournant sur le matériel informatique et la papeterie."
        }
    )
    if audit.items.count() == 0:
        for p in created_products[:5]:
            stock_cur = ProductStock.objects.filter(organization=org, product=p, warehouse=central_wh).first()
            qty_th = stock_cur.quantity_on_hand if stock_cur else Decimal("0.00")
            InventoryAuditItem.objects.create(
                organization=org,
                audit=audit,
                product=p,
                theoretical_quantity=qty_th,
                physical_quantity=qty_th,
                unit_cost=p.purchase_price
            )

    print("[+] Session d'audit physique initialisee.")
    print("[+] Peuplement du module Gestion des Stocks termine avec succes !")

if __name__ == '__main__':
    seed_inventory()


if __name__ == '__main__':
    seed_inventory()
