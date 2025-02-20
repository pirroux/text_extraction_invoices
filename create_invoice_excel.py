import pandas as pd
from datetime import datetime
import json
import re
import pytz  # Pour gérer les fuseaux horaires

def load_invoice_data():
    """Charge les données des factures depuis le fichier JSON"""
    try:
        with open('factures.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print("Erreur: Le fichier factures.json n'a pas été trouvé")
        return {}
    except json.JSONDecodeError:
        print("Erreur: Le fichier factures.json n'est pas un JSON valide")
        return {}

def create_invoice_dataframe(invoices_data):
    """Crée un DataFrame avec les headers spécifiés"""
    # Définir tous les headers possibles
    all_headers = ['Type-facture', 'n°ordre', 'saisie', 'Syst', 'N° Syst.', 'comptable',
                  'Type_Vente', 'Réseau_Vente', 'Client', 'Typologie', 'Banque créditée',
                  'Date commande', 'Date facture', 'Date expédition', 'Commentaire',
                  'date1', 'acompte1', 'date2', 'acompte2', 'Date solde', 'solde',
                  'contrôle paiement', 'reste dû', 'AVO', 'tva', 'ttc', 'Credit TTC',
                  'Credit HT', 'remise', 'TVA Collectee', 'quantité']

    # Ajouter les headers pour les 20 articles
    for i in range(1, 21):
        all_headers.extend([f'supfam{i}', f'fam{i}', f'ref{i}', f'q{i}', f'prix{i}',
                          f'r€{i}', f'ht{i}', f'tva€{i}'])

    rows = []
    for filename, invoice in invoices_data.items():
        try:
            if 'error' in invoice:
                continue

            data = invoice.get('data', {})
            if not data:
                continue

            # Création d'une ligne de base avec tous les headers vides
            row = dict.fromkeys(all_headers, '')

            # Extraire et formater la date selon le type de facture
            date = data.get('date', '')
            if data.get('type') == 'internet' and 'text' in invoice:
                # Pour les factures internet, chercher "Date de commande" dans le texte
                date_match = re.search(r'Date de commande\s*:\s*(\d{1,2}\s*\w+\s*\d{4})', invoice['text'])
                if date_match:
                    try:
                        # Convertir la date française en format YYYY-MM-DD
                        date_fr = date_match.group(1).strip()
                        # Remplacer les mois français par leur numéro
                        mois_fr = {
                            'janvier': '01', 'février': '02', 'mars': '03', 'avril': '04',
                            'mai': '05', 'juin': '06', 'juillet': '07', 'août': '08',
                            'septembre': '09', 'octobre': '10', 'novembre': '11', 'décembre': '12'
                        }
                        for mois, num in mois_fr.items():
                            date_fr = date_fr.replace(mois, num)

                        # Parser la date
                        jour, mois, annee = re.match(r'(\d{1,2})\s*(\d{2})\s*(\d{4})', date_fr).groups()
                        date = f"{annee}-{mois}-{jour.zfill(2)}"
                    except Exception as e:
                        print(f"Erreur lors du parsing de la date pour {filename}: {str(e)}")

            # Extraire le numéro de commande et les 5 derniers chiffres
            numero_facture = data.get('numero_facture', '')
            last_5_digits = numero_facture[-5:] if len(numero_facture) >= 5 else numero_facture

            # Extraire les premiers XX.XX de categorie_vente
            categorie_vente = data.get('categorie_vente', '')
            type_vente_match = re.match(r'\d{2}\.\d{2}', categorie_vente)
            type_vente = type_vente_match.group(0) if type_vente_match else categorie_vente

            # Remplir les données disponibles
            row.update({
                'Type-facture': numero_facture,
                'n°ordre': last_5_digits,
                'Type_Vente': data.get('Type_Vente', ''),
                'Réseau_Vente': data.get('Réseau_Vente', ''),
                'Client': data.get('client_name', ''),
                'Date commande': date,
                'Date facture': date,
                'Commentaire': data.get('commentaire', ''),
                'acompte1': data.get('TOTAL', {}).get('acompte', ''),
                'solde': data.get('TOTAL', {}).get('total_ttc', 0),
                'contrôle paiement': data.get('statut_paiement', ''),
                'Credit TTC': data.get('TOTAL', {}).get('total_ttc', 0),
                'Credit HT': data.get('TOTAL', {}).get('total_ht', 0),
                'TVA Collectee': data.get('TOTAL', {}).get('tva', 0),
                'quantité': data.get('nombre_articles', 0),
                'remise': data.get('TOTAL', {}).get('remise', '')
            })

            # Ajouter les informations pour chaque article
            articles = data.get('articles', [])
            for i, article in enumerate(articles, 1):
                if i > 20:  # Limite de 20 articles
                    break

                row.update({
                    f'ref{i}': article.get('reference', ''),
                    f'q{i}': article.get('quantite', ''),
                    f'prix{i}': article.get('prix_unitaire', ''),
                    f'ht{i}': article.get('montant_ht', ''),
                    f'tva€{i}': article.get('tva', ''),  # TVA directe de l'article
                    f'r€{i}': article.get('remise', ''),  # Remise directe de l'article
                })

            rows.append(row)

        except Exception as e:
            print(f"Erreur lors du traitement de {filename}: {str(e)}")
            continue

    # Créer le DataFrame avec les colonnes dans le bon ordre
    return pd.DataFrame(rows, columns=all_headers)

def format_excel(writer, df):
    """Applique le formatage au fichier Excel"""
    try:
        workbook = writer.book
        worksheet = writer.sheets['Factures']

        # Définir la largeur des colonnes
        for idx, col in enumerate(df.columns):
            max_length = max(
                df[col].astype(str).apply(len).max(),
                len(str(col))
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

    except Exception as e:
        print(f"Erreur lors du formatage Excel: {str(e)}")

def main():
    try:
        # Charger les données
        invoices_data = load_invoice_data()
        if not invoices_data:
            print("Aucune donnée à traiter")
            return

        # Créer le DataFrame
        df = create_invoice_dataframe(invoices_data)
        if df.empty:
            print("Aucune donnée valide à exporter")
            return

        # Générer le nom du fichier avec la date et l'heure au format YYMMDDHHMMSS en GMT+1
        paris_tz = pytz.timezone('Europe/Paris')
        current_time = datetime.now(paris_tz)

        # Format détaillé :
        # %y : année sur 2 chiffres
        # %m : mois sur 2 chiffres
        # %d : jour sur 2 chiffres
        # %H : heure sur 2 chiffres (format 24h)
        # %M : minutes sur 2 chiffres
        # %S : secondes sur 2 chiffres
        timestamp = current_time.strftime('%y%m%d%H%M%S')

        filename = f'factures_auto_{timestamp}.xlsx'

        # Créer le fichier Excel avec formatage
        with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Factures', index=False)
            format_excel(writer, df)

        print(f"Fichier Excel créé : {filename}")

    except Exception as e:
        print(f"Erreur lors de l'exécution: {str(e)}")

if __name__ == "__main__":
    main()
