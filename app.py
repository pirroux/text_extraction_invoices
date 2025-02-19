import streamlit as st
from excel_data_mapping import load_mappings
import time
from pathlib import Path

def get_mappings():
    """Récupère les mappings avec vérification de mise à jour"""
    # Chemin vers le fichier Excel partagé
    excel_path = st.secrets["mapping_path"]  # Configuré dans .streamlit/secrets.toml

    # Vérifie si le fichier existe
    if not Path(excel_path).exists():
        st.error(f"Fichier de mapping non trouvé. Veuillez vérifier le chemin: {excel_path}")
        return None

    # Utilise le cache Streamlit avec vérification de modification
    @st.cache_data(ttl=60)  # Cache d'1 minute
    def _load_mappings(file_mtime):
        return load_mappings(excel_path)

    # Obtient la dernière modification du fichier
    file_mtime = Path(excel_path).stat().st_mtime

    return _load_mappings(file_mtime)

def main():
    st.title("Extracteur de Factures Nomads Surfing")

    # Charge les mappings
    mappings = get_mappings()

    if mappings:
        # Affiche la dernière mise à jour
        st.sidebar.info(f"Dernière mise à jour des mappings: {time.ctime(mappings['last_update'])}")

        # Bouton pour forcer le rechargement
        if st.sidebar.button("Recharger les mappings"):
            st.cache_data.clear()
            st.rerun()

    # Reste de votre interface...

if __name__ == "__main__":
    main()
