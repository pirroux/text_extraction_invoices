import pandas as pd
from datetime import datetime
import json

def load_invoice_data():
    """Charge les données des factures depuis le fichier JSON"""
    with open('factures.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def create_invoice_dataframe(invoices_data):
    """Crée un DataFrame avec les headers spécifiés"""
    rows = []

    for filename, invoice in invoices_data.items():
        if 'error' in invoice:
            continue

        data = invoice['data']

        # Création d'une ligne de base avec tous les headers vides
        row = {
            'Type-facture': data.get('type', ''),
            'n°ordre': '',  # À remplir manuellement
            'saisie': '',   # À remplir manuellement
            'Syst': '',     # À remplir manuellement
            'N° Syst.': '', # À remplir manuellement
            'comptable': '', # À remplir manuellement
            'Type_Vente': data.get('categorie_vente', ''),
            'Réseau_Vente': 'Internet' if data['type'] == 'internet' else 'MEG',
            'Client': data.get('client_name', ''),
            'Typologie': '', # À remplir manuellement
            'Banque créditée': '', # À remplir manuellement
            'Date commande': data.get('date', ''),
            'Date facture': data.get('date', ''),
            'Date expédition': '', # À remplir manuellement
            'Commentaire': data.get('commentaire', ''),
            'date1': '', # Pour les acomptes
            'acompte1': data['TOTAL'].get('acompte', ''),
            'date2': '',
            'acompte2': '',
            'Date solde': '',
            'solde': '',
            'contrôle paiement': data.get('statut_paiement', ''),
            'reste dû': '',
            'AVO': '',
            'tva': data['TOTAL'].get('tva', 0),
            'ttc': data['TOTAL'].get('total_ttc', 0),
            'Credit TTC': data['TOTAL'].get('total_ttc', 0),
            'Credit HT': data['TOTAL'].get('total_ht', 0),
            'remise': '',
            'TVA Collectee': data['TOTAL'].get('tva', 0),
            'quantité': data.get('nombre_articles', 0),
        }

        # Ajouter les informations pour chaque article (jusqu'à 20 articles)
        articles = data.get('articles', [])
        for i, article in enumerate(articles, 1):
            if i > 20:  # Limite de 20 articles
                break

            prefix = f'Supfam{i}'
            row.update({
                f'supfam{i}': '',  # À remplir manuellement
                f'fam{i}': '',     # À remplir manuellement
                f'ref{i}': article.get('reference', ''),
                f'q{i}': article.get('quantite', ''),
                f'prix{i}': article.get('prix_unitaire', ''),
                f'r€{i}': '',      # Remise en euros
                f'ht{i}': article.get('montant_ht', ''),
                f'tva€{i}': article.get('tva', '') * article.get('montant_ht', 0) / 100 if article.get('tva') else '',
            })

        rows.append(row)

    return pd.DataFrame(rows)

def format_excel(writer, df):
    """Applique le formatage au fichier Excel"""
    workbook = writer.book
    worksheet = writer.sheets['Factures']

    # Définir la largeur des colonnes
    for idx, col in enumerate(df.columns):
        max_length = max(
            df[col].astype(str).apply(len).max(),
            len(col)
        ) + 2
        worksheet.set_column(idx, idx, max_length)

    # Créer des formats
    header_format = workbook.add_format({
        'bold': True,
        'text_wrap': True,
        'valign': 'top',
        'bg_color': '#D9E1F2',
        'border': 1
    })

    # Appliquer le format aux en-têtes
    for col_num, value in enumerate(df.columns.values):
        worksheet.write(0, col_num, value, header_format)

def main():
    # Charger les données
    invoices_data = load_invoice_data()

    # Créer le DataFrame
    df = create_invoice_dataframe(invoices_data)

    # Générer le nom du fichier avec la date et l'heure
    timestamp = datetime.now().strftime('%m_%d_%H_%M')
    filename = f'factures_auto_{timestamp}.xlsx'

    # Créer le fichier Excel avec formatage
    with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Factures', index=False)
        format_excel(writer, df)

    print(f"Fichier Excel créé : {filename}")

if __name__ == "__main__":
    main()
