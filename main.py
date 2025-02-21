from pathlib import Path
import json
from pdf_extractor import extract_text_from_pdf
from data_extractor import extract_data
from create_invoice_excel import create_excel_from_data
from billing_extractor import InvoiceExtractor
import logging

logger = logging.getLogger(__name__)

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

def process_pdfs(pdf_paths: list[Path]) -> Path:
    """Process multiple PDF files and create a single Excel file"""
    try:
        # Dictionary to store all invoice data
        all_invoices = {}

        # Create invoice extractor
        invoice_extractor = InvoiceExtractor()

        # Process each PDF
        for pdf_path in pdf_paths:
            try:
                logger.info(f"Processing {pdf_path.name}...")

                # Extract text from PDF
                extracted = extract_text_from_pdf(str(pdf_path))
                if not extracted:
                    logger.warning(f"No text extracted from {pdf_path.name}")
                    continue

                # Extract structured data using the invoice extractor
                data = invoice_extractor.extract_invoice_data(extracted['text'])

                # Add to main dictionary with the same structure as before
                all_invoices[pdf_path.name] = {
                    'text': extracted['text'],
                    'data': data['invoice_data']
                }

                logger.info(f"Successfully processed {pdf_path.name}")

            except Exception as e:
                logger.error(f"Error processing {pdf_path.name}: {str(e)}")
                all_invoices[pdf_path.name] = {
                    'error': str(e)
                }

        if not all_invoices:
            raise ValueError("No invoices were successfully processed")

        # Save to JSON for debugging (optional)
        json_path = Path("factures.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(all_invoices, f, ensure_ascii=False, indent=2)

        # Create Excel file from the processed data
        excel_path = create_excel_from_data(all_invoices)

        if not excel_path.exists():
            raise FileNotFoundError("Excel file was not created")

        return excel_path

    except Exception as e:
        logger.error(f"Error in process_pdfs: {str(e)}")
        raise

def process_pdf(pdf_path: Path) -> Path:
    """Process a single PDF file - wrapper around process_pdfs"""
    return process_pdfs([pdf_path])

if __name__ == "__main__":
    # Test processing
    pdf_folder = Path("data_factures/facturesv3")
    pdfs = list(pdf_folder.glob("*.pdf"))
    if pdfs:
        try:
            excel_path = process_pdfs(pdfs)
            print(f"Excel file created at: {excel_path}")
        except Exception as e:
            print(f"Error: {str(e)}")
    else:
        print("No PDF files found in data_factures folder")
