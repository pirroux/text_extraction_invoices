import pdfplumber
from typing import Dict, Optional

def extract_text_from_pdf(pdf_path: str) -> Optional[Dict]:
    """Extrait le texte et les tables d'un PDF en utilisant pdfplumber"""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            # Initialisation des données
            text = ""
            tables = []

            # Extraction page par page
            for page in pdf.pages:
                # Extraction du texte
                text += page.extract_text() or ""

                # Extraction des tables
                page_tables = page.extract_tables()
                if page_tables:
                    tables.extend(page_tables)

            # Construction du résultat
            result = {
                'text': text,
                'type': 'meg',  # Par défaut
                'data': {
                    'type': 'meg'
                }
            }

            # Si des tables ont été trouvées, les ajouter au résultat
            if tables:
                result['tables'] = tables

            return result

    except Exception as e:
        print(f"Erreur lors de l'extraction du PDF {pdf_path}: {str(e)}")
        return None
