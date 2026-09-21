"""
reports.py — Génération des rapports PDF du module caille (via reportlab,
une bibliothèque 100% Python, sans dépendance système — compatible avec un
environnement serverless comme Vercel).
"""
import io
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

PRIMARY = colors.HexColor("#6e4622")
ACCENT_BG = colors.HexColor("#f0e8db")


def _doc(buffer, title):
    doc = SimpleDocTemplate(buffer, pagesize=A4, title=title,
                             topMargin=1.5 * cm, bottomMargin=1.5 * cm,
                             leftMargin=1.5 * cm, rightMargin=1.5 * cm)
    styles = getSampleStyleSheet()
    elements = [Paragraph(title, styles["Title"]), Spacer(1, 0.4 * cm)]
    return doc, elements, styles


def _table_style(nb_cols, header=True, total_row=True):
    style = [
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
    ]
    if header:
        style += [
            ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ]
    if total_row:
        style += [
            ("BACKGROUND", (0, -1), (-1, -1), ACCENT_BG),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ]
    return TableStyle(style)


def rapport_ponte(entrees, date_debut, date_fin, totaux):
    buffer = io.BytesIO()
    doc, elements, styles = _doc(buffer, "Rapport de ponte &amp; ventes d'œufs")
    elements.append(Paragraph(
        f"Période : {date_debut.strftime('%d/%m/%Y')} au {date_fin.strftime('%d/%m/%Y')}",
        styles["Normal"]))
    elements.append(Spacer(1, 0.4 * cm))

    data = [["Date", "Lot", "Pondus", "Vendus (u)", "Prix/u (F)", "Plateaux", "Prix/plateau (F)", "Montant (F)", "Cassés", "Autoconso."]]
    for e in entrees:
        data.append([
            e.date_jour.strftime("%d/%m/%Y"), e.lot.nom, e.oeufs_pondus, e.oeufs_vendus,
            e.prix_unitaire_vente, e.plateaux_vendus, e.prix_plateau_vente,
            e.montant_vente, e.oeufs_casses, e.oeufs_autoconsommes,
        ])
    data.append(["", "TOTAL", totaux["pondus"], totaux["vendus"], "", "", "", totaux["revenu"], totaux["casses"], ""])

    if len(data) == 2:
        elements.append(Paragraph("Aucune donnée sur cette période.", styles["Normal"]))
    else:
        t = Table(data, repeatRows=1)
        t.setStyle(_table_style(len(data[0])))
        elements.append(t)

    doc.build(elements)
    buffer.seek(0)
    return buffer


def rapport_mortalite(entrees, date_debut, date_fin, totaux):
    buffer = io.BytesIO()
    doc, elements, styles = _doc(buffer, "Rapport de mortalité")
    elements.append(Paragraph(
        f"Période : {date_debut.strftime('%d/%m/%Y')} au {date_fin.strftime('%d/%m/%Y')}",
        styles["Normal"]))
    elements.append(Spacer(1, 0.4 * cm))

    data = [["Date", "Lot", "Adultes morts", "Jeunes morts", "Cause", "Notes"]]
    for e in entrees:
        data.append([
            e.date_jour.strftime("%d/%m/%Y"), e.lot.nom, e.cailles_mortes,
            e.cailletons_morts, e.cause or "", e.notes or "",
        ])
    data.append(["", "TOTAL", totaux["cailles"], totaux["cailletons"], "", ""])

    if len(data) == 2:
        elements.append(Paragraph("Aucune donnée sur cette période.", styles["Normal"]))
    else:
        t = Table(data, repeatRows=1)
        t.setStyle(_table_style(len(data[0])))
        elements.append(t)

    doc.build(elements)
    buffer.seek(0)
    return buffer


def rapport_achats(achats, date_debut, date_fin, totaux):
    buffer = io.BytesIO()
    doc, elements, styles = _doc(buffer, "Rapport des achats d'alimentation")
    elements.append(Paragraph(
        f"Période : {date_debut.strftime('%d/%m/%Y')} au {date_fin.strftime('%d/%m/%Y')}",
        styles["Normal"]))
    elements.append(Spacer(1, 0.4 * cm))

    data = [["Date", "Type", "Fournisseur", "Quantité (kg)", "Prix total (F)", "Prix/kg (F)"]]
    for a in achats:
        data.append([
            a.date_achat.strftime("%d/%m/%Y"), a.type_provende.nom,
            a.fournisseur.nom if a.fournisseur else "—",
            a.quantite_kg, a.prix_total, a.prix_unitaire_kg,
        ])
    data.append(["", "TOTAL", "", totaux["kg"], totaux["cout"], ""])

    if len(data) == 2:
        elements.append(Paragraph("Aucun achat sur cette période.", styles["Normal"]))
    else:
        t = Table(data, repeatRows=1)
        t.setStyle(_table_style(len(data[0])))
        elements.append(t)

    doc.build(elements)
    buffer.seek(0)
    return buffer


def fiche_lot(lot, pontes, mortalites, naissances):
    buffer = io.BytesIO()
    doc, elements, styles = _doc(buffer, f"Fiche du lot : {lot.nom}")

    infos = [
        ["Type", lot.type_lot],
        ["Mise en place", lot.date_mise_en_place.strftime("%d/%m/%Y")],
        ["Effectif initial", str(lot.effectif_initial)],
        ["Effectif actuel", str(lot.effectif_actuel)],
        ["Statut", lot.statut],
        ["Œufs pondus (total)", str(lot.total_oeufs_pondus)],
        ["Revenu œufs (total)", f"{lot.total_revenu_oeufs} F"],
        ["Mortalité adultes (total)", str(lot.total_mortalite_cailles)],
        ["Mortalité jeunes (total)", str(lot.total_mortalite_cailletons)],
    ]
    t_info = Table(infos, colWidths=[6 * cm, 8 * cm])
    t_info.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("BACKGROUND", (0, 0), (0, -1), ACCENT_BG),
    ]))
    elements.append(t_info)
    elements.append(Spacer(1, 0.6 * cm))

    def sous_tableau(titre, entetes, lignes):
        elements.append(Paragraph(titre, styles["Heading3"]))
        if not lignes:
            elements.append(Paragraph("Aucune donnée.", styles["Normal"]))
        else:
            data = [entetes] + lignes
            t = Table(data, repeatRows=1)
            t.setStyle(_table_style(len(entetes), total_row=False))
            elements.append(t)
        elements.append(Spacer(1, 0.5 * cm))

    sous_tableau("Ponte & ventes", ["Date", "Pondus", "Vendus", "Montant (F)"],
                 [[p.date_jour.strftime("%d/%m/%Y"), p.oeufs_pondus, p.oeufs_vendus, p.montant_vente] for p in pontes])
    sous_tableau("Mortalité", ["Date", "Adultes", "Jeunes", "Cause"],
                 [[m.date_jour.strftime("%d/%m/%Y"), m.cailles_mortes, m.cailletons_morts, m.cause or ""] for m in mortalites])
    sous_tableau("Naissances", ["Date", "Nombre", "Origine"],
                 [[n.date_jour.strftime("%d/%m/%Y"), n.nombre_cailletons, n.origine] for n in naissances])

    doc.build(elements)
    buffer.seek(0)
    return buffer


def rapport_naissances(entrees, date_debut, date_fin, total):
    buffer = io.BytesIO()
    doc, elements, styles = _doc(buffer, "Rapport des naissances")
    elements.append(Paragraph(
        f"Période : {date_debut.strftime('%d/%m/%Y')} au {date_fin.strftime('%d/%m/%Y')}",
        styles["Normal"]))
    elements.append(Spacer(1, 0.4 * cm))

    data = [["Date", "Lot", "Nombre", "Origine", "Notes"]]
    for e in entrees:
        data.append([
            e.date_jour.strftime("%d/%m/%Y"), e.lot.nom, e.nombre_cailletons,
            "Éclosion" if e.origine == "eclosion" else "Achat", e.notes or "",
        ])
    data.append(["", "TOTAL", total, "", ""])

    if len(data) == 2:
        elements.append(Paragraph("Aucune donnée sur cette période.", styles["Normal"]))
    else:
        t = Table(data, repeatRows=1)
        t.setStyle(_table_style(len(data[0])))
        elements.append(t)

    doc.build(elements)
    buffer.seek(0)
    return buffer


def rapport_consommation(entrees, date_debut, date_fin, total_kg):
    buffer = io.BytesIO()
    doc, elements, styles = _doc(buffer, "Rapport de consommation d'alimentation")
    elements.append(Paragraph(
        f"Période : {date_debut.strftime('%d/%m/%Y')} au {date_fin.strftime('%d/%m/%Y')}",
        styles["Normal"]))
    elements.append(Spacer(1, 0.4 * cm))

    data = [["Date", "Lot", "Type", "Quantité (kg)", "Notes"]]
    for c in entrees:
        data.append([
            c.date_jour.strftime("%d/%m/%Y"), c.lot.nom if c.lot else "Tous lots",
            c.type_provende.nom, c.quantite_kg, c.notes or "",
        ])
    data.append(["", "", "TOTAL", total_kg, ""])

    if len(data) == 2:
        elements.append(Paragraph("Aucune donnée sur cette période.", styles["Normal"]))
    else:
        t = Table(data, repeatRows=1)
        t.setStyle(_table_style(len(data[0])))
        elements.append(t)

    doc.build(elements)
    buffer.seek(0)
    return buffer


def rapport_taches(taches, filtre_statut):
    buffer = io.BytesIO()
    doc, elements, styles = _doc(buffer, "Cahier de charges — tâches &amp; protocoles")
    libelle_filtre = {"tous": "Toutes", "a_faire": "À faire", "en_cours": "En cours", "fait": "Terminées"}
    elements.append(Paragraph(f"Filtre : {libelle_filtre.get(filtre_statut, 'Toutes')}", styles["Normal"]))
    elements.append(Spacer(1, 0.4 * cm))

    libelle_statut = {"a_faire": "À faire", "en_cours": "En cours", "fait": "Fait"}
    data = [["Titre", "Catégorie", "Lot", "Date prévue", "Récurrence", "Statut"]]
    for t in taches:
        data.append([
            t.titre, t.categorie, t.lot.nom if t.lot else "—",
            t.date_prevue.strftime("%d/%m/%Y") if t.date_prevue else "—",
            t.recurrence or "aucune", libelle_statut.get(t.statut, t.statut),
        ])

    if len(data) == 1:
        elements.append(Paragraph("Aucune tâche pour ce filtre.", styles["Normal"]))
    else:
        t_tab = Table(data, repeatRows=1)
        t_tab.setStyle(_table_style(len(data[0]), total_row=False))
        elements.append(t_tab)

    doc.build(elements)
    buffer.seek(0)
    return buffer


def rapport_fournisseurs(fournisseurs):
    buffer = io.BytesIO()
    doc, elements, styles = _doc(buffer, "Liste des fournisseurs")

    data = [["Nom", "Contact", "Adresse", "Notes"]]
    for f in fournisseurs:
        data.append([f.nom, f.contact or "—", f.adresse or "—", f.notes or ""])

    if len(data) == 1:
        elements.append(Paragraph("Aucun fournisseur enregistré.", styles["Normal"]))
    else:
        t = Table(data, repeatRows=1)
        t.setStyle(_table_style(len(data[0]), total_row=False))
        elements.append(t)

    doc.build(elements)
    buffer.seek(0)
    return buffer


def rapport_depenses(entrees, date_debut, date_fin, total):
    buffer = io.BytesIO()
    doc, elements, styles = _doc(buffer, "Rapport des dépenses diverses")
    elements.append(Paragraph(
        f"Période : {date_debut.strftime('%d/%m/%Y')} au {date_fin.strftime('%d/%m/%Y')}",
        styles["Normal"]))
    elements.append(Spacer(1, 0.4 * cm))

    data = [["Date", "Catégorie", "Lot", "Montant (F)", "Notes"]]
    for d in entrees:
        data.append([
            d.date_depense.strftime("%d/%m/%Y"), d.categorie,
            d.lot.nom if d.lot else "—", d.montant, d.notes or "",
        ])
    data.append(["", "", "TOTAL", total, ""])

    if len(data) == 2:
        elements.append(Paragraph("Aucune dépense sur cette période.", styles["Normal"]))
    else:
        t = Table(data, repeatRows=1)
        t.setStyle(_table_style(len(data[0])))
        elements.append(t)

    doc.build(elements)
    buffer.seek(0)
    return buffer


def rapport_personnel(employes):
    buffer = io.BytesIO()
    doc, elements, styles = _doc(buffer, "Liste du personnel")

    data = [["Nom", "Rôle", "Téléphone", "Embauché le", "Statut"]]
    for e in employes:
        data.append([
            e.nom, e.role or "—", e.telephone or "—",
            e.date_embauche.strftime("%d/%m/%Y") if e.date_embauche else "—",
            "Actif" if e.statut == "actif" else "Inactif",
        ])

    if len(data) == 1:
        elements.append(Paragraph("Aucun employé enregistré.", styles["Normal"]))
    else:
        t = Table(data, repeatRows=1)
        t.setStyle(_table_style(len(data[0]), total_row=False))
        elements.append(t)

    doc.build(elements)
    buffer.seek(0)
    return buffer


def rapport_sante(entrees, date_debut, date_fin, libelles_type):
    buffer = io.BytesIO()
    doc, elements, styles = _doc(buffer, "Carnet de santé")
    elements.append(Paragraph(
        f"Période : {date_debut.strftime('%d/%m/%Y')} au {date_fin.strftime('%d/%m/%Y')}",
        styles["Normal"]))
    elements.append(Spacer(1, 0.4 * cm))

    data = [["Date", "Lot", "Type", "Produit", "Réalisé par", "Notes"]]
    for s in entrees:
        data.append([
            s.date_soin.strftime("%d/%m/%Y"), s.lot.nom, libelles_type.get(s.type_soin, s.type_soin),
            s.produit or "—", s.employe.nom if s.employe else "—", s.notes or "",
        ])

    if len(data) == 1:
        elements.append(Paragraph("Aucun soin sur cette période.", styles["Normal"]))
    else:
        t = Table(data, repeatRows=1)
        t.setStyle(_table_style(len(data[0]), total_row=False))
        elements.append(t)

    doc.build(elements)
    buffer.seek(0)
    return buffer


def rapport_clients(clients):
    buffer = io.BytesIO()
    doc, elements, styles = _doc(buffer, "Carnet clients")

    data = [["Nom", "Téléphone", "Adresse", "Notes"]]
    for c in clients:
        data.append([c.nom, c.telephone or "—", c.adresse or "—", c.notes or ""])

    if len(data) == 1:
        elements.append(Paragraph("Aucun client enregistré.", styles["Normal"]))
    else:
        t = Table(data, repeatRows=1)
        t.setStyle(_table_style(len(data[0]), total_row=False))
        elements.append(t)

    doc.build(elements)
    buffer.seek(0)
    return buffer


def rapport_ventes(entrees, date_debut, date_fin, total):
    buffer = io.BytesIO()
    doc, elements, styles = _doc(buffer, "Carnet de ventes")
    elements.append(Paragraph(
        f"Période : {date_debut.strftime('%d/%m/%Y')} au {date_fin.strftime('%d/%m/%Y')}",
        styles["Normal"]))
    elements.append(Spacer(1, 0.4 * cm))

    data = [["Date", "Client", "Produit", "Qté", "Unité", "Prix/u (F)", "Montant (F)"]]
    for v in entrees:
        data.append([
            v.date_vente.strftime("%d/%m/%Y"), v.client.nom if v.client else "—", v.produit,
            v.quantite, v.unite, v.prix_unitaire, v.montant_total,
        ])
    data.append(["", "", "", "", "", "TOTAL", total])

    if len(data) == 2:
        elements.append(Paragraph("Aucune vente sur cette période.", styles["Normal"]))
    else:
        t = Table(data, repeatRows=1)
        t.setStyle(_table_style(len(data[0])))
        elements.append(t)

    doc.build(elements)
    buffer.seek(0)
    return buffer


def rapport_croissance(entrees, lot_nom):
    buffer = io.BytesIO()
    titre = f"Suivi de croissance — {lot_nom}" if lot_nom else "Suivi de croissance — tous les lots"
    doc, elements, styles = _doc(buffer, titre)

    data = [["Date", "Lot", "Poids moyen (g)", "Échantillon", "Notes"]]
    for p in entrees:
        data.append([
            p.date_pesee.strftime("%d/%m/%Y"), p.lot.nom if p.lot else "—", p.poids_moyen_g,
            p.nombre_pese or "—", p.notes or "",
        ])

    if len(data) == 1:
        elements.append(Paragraph("Aucune pesée enregistrée.", styles["Normal"]))
    else:
        t = Table(data, repeatRows=1)
        t.setStyle(_table_style(len(data[0]), total_row=False))
        elements.append(t)

    doc.build(elements)
    buffer.seek(0)
    return buffer