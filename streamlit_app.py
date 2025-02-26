import streamlit as st
import requests
import os
from dotenv import load_dotenv
from create_invoice_excel import create_invoice_dataframe, format_excel, load_invoice_data
import pandas as pd
from datetime import datetime
import pytz
import json
from pathlib import Path
from pdf_extractor import extract_text_from_pdf
from billing_extractor import InvoiceExtractor

# Set page configuration (must be the first Streamlit command)
st.set_page_config(
    page_title="Analyse de Factures PDF",
    page_icon="📊",
    layout="centered"
)

# Function to reload environment variables
def reload_env():
    load_dotenv()

# Initial load of environment variables
reload_env()

# Configuration de l'API endpoint
API_URL = os.getenv("API_URL", "http://fastapi:8000")
PROJECT_ID = os.getenv("PROJECT_ID", "nomadsfacturation")

# Create temp_files directory if it doesn't exist
os.makedirs('temp_files', exist_ok=True)

# Centrer le titre Nomads Surfing
st.markdown("<h1 style='text-align: center;'>Nomads Surfing 🌊</h1>", unsafe_allow_html=True)

# Centrer le sous-titre sur une seule ligne
st.markdown("<h2 style='text-align: center;'>Analyse automatique de factures PDF</h2>", unsafe_allow_html=True)

# Upload multiple PDF files
uploaded_files = st.file_uploader(" ", type="pdf", accept_multiple_files=True)

def process_pdfs_locally(uploaded_files):
    """Process PDFs locally using the same logic as app.py"""
    # Initialiser l'extracteur
    extractor = InvoiceExtractor()

    # Dictionnaire pour stocker les données des factures
    invoices_data = {}

    # Traiter chaque PDF
    for uploaded_file in uploaded_files:
        try:
            # Save the PDF locally
            pdf_path = os.path.join('temp_files', uploaded_file.name)
            with open(pdf_path, 'wb') as f:
                f.write(uploaded_file.getvalue())

            # Extract text from PDF
            extracted_data = extract_text_from_pdf(pdf_path)
            text = extracted_data.get('text', '')

            # Extract invoice data
            data = extractor.extract_invoice_data(text)

            # Calculate total quantity from articles
            total_quantity = 0
            articles = data.get("invoice_data", {}).get("articles", [])
            for article in articles:
                try:
                    qty = float(article.get("quantite", 0))
                    total_quantity += qty
                except (ValueError, TypeError):
                    st.warning(f"Could not convert quantity to number: {article.get('quantite')}")

            # Update nombre_articles with the actual sum of quantities
            if "invoice_data" in data:
                data["invoice_data"]["nombre_articles"] = total_quantity

            # Store data in the format expected by create_invoice_dataframe
            invoices_data[uploaded_file.name] = {
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
            st.error(f"Error processing {uploaded_file.name}: {str(e)}")

    # Save JSON data
    json_path = os.path.join('temp_files', 'factures.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(invoices_data, f, ensure_ascii=False, indent=2)

    # Generate Excel filename
    paris_tz = pytz.timezone('Europe/Paris')
    current_time = datetime.now(paris_tz)
    timestamp = current_time.strftime('%y%m%d%H%M%S')
    filename = f'factures_auto_{timestamp}.xlsx'
    excel_path = os.path.join('temp_files', filename)

    # Create DataFrame using the same function as app.py
    df = create_invoice_dataframe(invoices_data)

    # Save with formatting
    with pd.ExcelWriter(excel_path, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Factures', index=False)
        format_excel(writer, df)

    return excel_path, filename, df

if uploaded_files:
    for uploaded_file in uploaded_files:
        st.write("📄 Fichier chargé :", uploaded_file.name)

    # Bouton pour lancer l'analyse
    if st.button("Analyser"):
        try:
            with st.spinner("🔄 Analyse en cours..."):
                # Process PDFs locally using the same logic as app.py
                excel_path, filename, df = process_pdfs_locally(uploaded_files)

                # Display summary information
                st.success("✅ Analyse des documents terminée avec succès ! 🎉")


                # Provide download button
                with open(excel_path, 'rb') as f:
                    excel_data = f.read()

                st.success(f"📂 Fichier Excel créé avec succès ! 🤙")

                st.download_button(
                    label=f"📎 Télécharger {filename}",
                    data=excel_data,
                    file_name=filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

        except Exception as e:
            st.error(f"🚨 Une erreur est survenue : {str(e)}")

# Add a footer with version information
st.markdown("---")
st.markdown("<div style='text-align: center; color: gray; font-size: 0.8em;'>Nomads Surfing - v1.0.0</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    # Remove the recursive call that's causing multiple instances
    pass
