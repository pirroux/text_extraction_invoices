from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
import shutil
from pathlib import Path
import tempfile
import uvicorn
import logging
import os
from datetime import datetime
import pytz
from typing import List
from pdf_extractor import extract_text_from_pdf
from billing_extractor import InvoiceExtractor
from create_invoice_excel import create_invoice_dataframe, format_excel
import json
import traceback
import pandas as pd

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Create temp_files directory if it doesn't exist
TEMP_DIR = Path("temp_files")
TEMP_DIR.mkdir(exist_ok=True)

def generate_excel_filename():
    """Génère un nom de fichier au format factures_auto_YYMMDDHHMMSS"""
    paris_tz = pytz.timezone('Europe/Paris')
    current_time = datetime.now(paris_tz)
    timestamp = current_time.strftime('%y%m%d%H%M%S')
    return f'factures_auto_{timestamp}.xlsx'

def process_pdfs(pdf_paths):
    """Traite les PDFs et génère un fichier Excel"""
    logger.info(f"Starting PDF processing for paths: {pdf_paths}")

    # Initialiser l'extracteur
    extractor = InvoiceExtractor()

    # Dictionnaire pour stocker les données des factures
    invoices_data = {}

    # Traiter chaque PDF
    for pdf_path in pdf_paths:
        try:
            logger.info(f"Processing file: {pdf_path}")

            # Get just the filename without the path
            filename = os.path.basename(pdf_path)

            # Vérifier que le fichier existe
            if not os.path.exists(str(pdf_path)):
                logger.error(f"File not found: {pdf_path}")
                continue

            # Extraire le texte du PDF
            logger.info("Extracting text...")
            extracted_data = extract_text_from_pdf(str(pdf_path))
            text = extracted_data.get('text', '')
            logger.info(f"Extracted text length: {len(text)}")

            # Extraire les données de la facture
            logger.info("Extracting invoice data...")
            data = extractor.extract_invoice_data(text)

            # Calculate total quantity from articles
            total_quantity = 0
            articles = data.get("invoice_data", {}).get("articles", [])
            for article in articles:
                total_quantity += article.get("quantite", 0)

            logger.info(f"Total quantity calculated: {total_quantity}")

            # Update nombre_articles with the actual sum of quantities
            if "invoice_data" in data:
                data["invoice_data"]["nombre_articles"] = total_quantity

            # Stocker les données dans le format attendu par create_invoice_dataframe
            invoices_data[filename] = {
                "text": text,
                "data": {
                    "type": data.get("invoice_data", {}).get("type", ""),
                    "TOTAL": data.get("invoice_data", {}).get("TOTAL", {}),
                    "articles": data.get("invoice_data", {}).get("articles", []),
                    "nombre_articles": total_quantity,  # Use calculated total
                    "Type_Vente": data.get("invoice_data", {}).get("Type_Vente", ""),
                    "Réseau_Vente": data.get("invoice_data", {}).get("Réseau_Vente", ""),
                    "commentaire": data.get("invoice_data", {}).get("commentaire", ""),
                    "statut_paiement": data.get("invoice_data", {}).get("statut_paiement", ""),
                    "numero_client": data.get("invoice_data", {}).get("numero_client", ""),
                    "client_name": data.get("invoice_data", {}).get("client_name", ""),
                    "date_facture": data.get("invoice_data", {}).get("date_facture", ""),
                    "date_commande": data.get("invoice_data", {}).get("date_commande", ""),
                    "numero_facture": data.get("invoice_data", {}).get("numero_facture", "")
                }
            }
        except Exception as e:
            logger.error(f"Error processing {pdf_path}: {str(e)}")
            logger.error(traceback.format_exc())
            raise Exception(f"Error processing {pdf_path}: {str(e)}")

    try:
        # Sauvegarder les données JSON
        logger.info("Saving JSON data...")
        json_path = TEMP_DIR / "factures.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(invoices_data, f, ensure_ascii=False, indent=2)

        logger.info(f"JSON data saved to {json_path}")

        # Générer le fichier Excel
        logger.info("Generating Excel file...")
        excel_path = TEMP_DIR / generate_excel_filename()

        # Créer le DataFrame
        df = create_invoice_dataframe(invoices_data)

        # Log the quantité column to verify it's correct
        if 'quantité' in df.columns:
            logger.info(f"Quantité values in DataFrame: {df['quantité'].tolist()}")

        # Sauvegarder avec le formatage
        with pd.ExcelWriter(excel_path, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Factures', index=False)
            format_excel(writer, df)

        return excel_path
    except Exception as e:
        logger.error(f"Error in final processing: {str(e)}")
        logger.error(traceback.format_exc())
        raise

@app.post("/analyze_pdfs/")
async def analyze_pdfs(files: List[UploadFile] = File(...)):
    try:
        # Create a list to store processed PDF paths
        pdf_paths = []

        # Process each uploaded file
        for file in files:
            # Verify file type
            if not file.filename.endswith('.pdf'):
                raise HTTPException(status_code=400, detail="All files must be PDFs")

            # Create unique name for the file
            pdf_name = f"input_{os.urandom(8).hex()}.pdf"
            pdf_path = TEMP_DIR / pdf_name
            pdf_paths.append(pdf_path)

            # Save the uploaded PDF
            with pdf_path.open("wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

        try:
            # Process all PDFs (maintenant appel direct à la fonction locale)
            excel_path = process_pdfs(pdf_paths)

            if not excel_path.exists():
                raise HTTPException(status_code=500, detail="Excel file was not created")

            # Generate filename with correct format
            excel_filename = generate_excel_filename()

            # Return Excel file
            headers = {
                'Content-Disposition': f'attachment; filename="{excel_filename}"'
            }

            return FileResponse(
                path=excel_path,
                filename=excel_filename,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                background=None,  # Prevent automatic deletion
                headers=headers
            )

        except Exception as e:
            logger.error(f"Error processing PDFs: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error processing PDFs: {str(e)}")

        finally:
            # Clean up temporary files
            for pdf_path in pdf_paths:
                try:
                    if pdf_path.exists():
                        pdf_path.unlink()
                except Exception as e:
                    logger.error(f"Error cleaning up files: {str(e)}")

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Nettoyage périodique des fichiers temporaires (optionnel)
@app.on_event("startup")
async def startup_event():
    try:
        for file in TEMP_DIR.glob("*"):
            file.unlink()
    except Exception as e:
        logger.error(f"Erreur lors du nettoyage initial: {str(e)}")

@app.get("/debug/json")
async def debug_json():
    """Endpoint to check the JSON data"""
    try:
        json_path = TEMP_DIR / "factures.json"
        if not json_path.exists():
            return {"error": "No JSON data found"}

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Return a summary to avoid overwhelming response
        summary = {}
        for filename, invoice in data.items():
            articles = invoice.get('data', {}).get('articles', [])
            total_qty = sum(article.get('quantite', 0) for article in articles)
            summary[filename] = {
                "article_count": len(articles),
                "total_quantity": total_qty,
                "nombre_articles": invoice.get('data', {}).get('nombre_articles', 0)
            }

        return {"summary": summary}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
