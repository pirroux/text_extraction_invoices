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

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Créer un dossier temporaire persistant pour les fichiers
TEMP_DIR = Path("temp_files")
TEMP_DIR.mkdir(exist_ok=True)

def generate_excel_filename():
    """Génère un nom de fichier au format factures_auto_YYMMDDHHMMSS"""
    paris_tz = pytz.timezone('Europe/Paris')
    current_time = datetime.now(paris_tz)
    timestamp = current_time.strftime('%y%m%d%H%M%S')
    return f'factures_auto_{timestamp}.xlsx'

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
            # Process all PDFs
            from main import process_pdfs  # You'll need to create this function
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

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
