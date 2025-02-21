#!/bin/bash

# Démarrage de FastAPI en arrière-plan
uvicorn app:app --host 0.0.0.0 --port 8000 &

# Démarrage de Streamlit
streamlit run streamlit_app.py --server.port 8501 --server.address 0.0.0.0
