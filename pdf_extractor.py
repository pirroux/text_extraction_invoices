import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extrait le texte d'un PDF en utilisant PyMuPDF et OCR si nécessaire"""
    try:
        # Ouvre le document
        doc = fitz.open(pdf_path)

        # Vérifie si le document est vide
        if doc.page_count == 0:
            print(f"Le PDF {pdf_path} ne contient aucune page")
            return ""

        # Essaie d'abord l'extraction normale
        text = []
        for page_num in range(doc.page_count):
            page = doc[page_num]
            page_text = page.get_text("text").strip()

            # Si pas de texte, essaie l'OCR
            if not page_text:
                print(f"Tentative d'OCR sur la page {page_num + 1}...")
                # Obtient l'image de la page
                pix = page.get_pixmap()
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                # Applique l'OCR
                page_text = pytesseract.image_to_string(img, lang='fra')

            if page_text.strip():
                text.append(page_text)
            else:
                print(f"Page {page_num + 1} vide ou non extractible")

        # Ferme le document
        doc.close()

        # Vérifie si du texte a été extrait
        if not text:
            print(f"Aucun texte extractible trouvé dans {pdf_path}")
            return ""

        return "\n".join(text)

    except Exception as e:
        print(f"Erreur lors de l'extraction du PDF {pdf_path}: {str(e)}")
        return ""
