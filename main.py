from pathlib import Path
import json
from pdf_extractor import extract_text_from_pdf
from billing_extractor import InvoiceExtractor

def load_patterns() -> dict:
    """Charge les patterns de reconnaissance de texte"""
    return {
        "general": {
            "Type-facture": r"(?i)N°\s*:\s*(FAC\d+)",
            "Client": r"(?i)(?:société|SARL|SA|SAS|EURL|SASU)?\s*([A-Z][A-Za-zÀ-ÿ\s\-']+)",
            "Date facture": r"(?i)Date\s*:\s*(\d{2}/\d{2}/\d{4})",
            "Credit TTC": r"Total\s+TTC\s*:?\s*(\d+[.,]\d+)\s*€"
        },
        "article_pattern": r"ART(\d+)\s*-([^\n]+?)\s+(\d+,\d+)\s+(\d+,\d+)\s*€\s*(\d+,\d+)%\s*(\d+,\d+)\s*€"
    }

def main():
    # Initialise les chemins
    pdf_folder = Path("data_factures/facturesv2")
    output_file = Path("factures.json")

    # Crée l'extracteur de factures (plus besoin de credentials)
    invoice_extractor = InvoiceExtractor()

    # Dictionnaire pour stocker toutes les factures
    all_invoices = {}

    # Traite chaque PDF
    for pdf_path in pdf_folder.glob("*.pdf"):
        try:
            print(f"\nTraitement de {pdf_path.name}...")

            # Extrait le texte avec pdfplumber
            extracted = extract_text_from_pdf(str(pdf_path))
            if not extracted:
                raise ValueError("Pas de texte extrait")

            # Utilise le nouvel extracteur pour obtenir les données structurées
            data = invoice_extractor.extract_invoice_data(extracted['text'])

            # Ajoute au dictionnaire principal
            all_invoices[pdf_path.name] = {
                'text': extracted['text'],
                'data': data['invoice_data']  # Notez le changement ici
            }

            print(f"✓ {pdf_path.name} traité avec succès")

        except Exception as e:
            print(f"✗ Erreur sur {pdf_path.name}: {str(e)}")
            all_invoices[pdf_path.name] = {
                'error': str(e)
            }

    # Sauvegarde toutes les factures dans un seul fichier JSON
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_invoices, f, ensure_ascii=False, indent=2)
    print(f"\nToutes les factures ont été sauvegardées dans {output_file}")

if __name__ == "__main__":
    main()
