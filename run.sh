#!/bin/bash

# Create temp_files directory if it doesn't exist
mkdir -p temp_files

# Check if we're in a virtual environment
if [[ -z "${VIRTUAL_ENV}" ]]; then
    echo "Activating virtual environment..."
    if [ -d "nomads_facturation" ]; then
        source nomads_facturation/bin/activate
    else
        echo "Virtual environment not found. Creating one..."
        python -m venv nomads_facturation
        source nomads_facturation/bin/activate
        pip install -r requirements.txt
    fi
fi

# Kill any existing FastAPI or Streamlit processes
echo "Cleaning up any existing processes..."
pkill -f "uvicorn app:app" || true
pkill -f "streamlit run" || true

# Clean up any temporary files
echo "Cleaning up temporary files..."
rm -f temp_files/factures.json
rm -f temp_files/factures*.xlsx

# Start FastAPI in the background
echo "Starting FastAPI server..."
uvicorn app:app --host 0.0.0.0 --port 8000 &
FASTAPI_PID=$!

# Wait for FastAPI to start
echo "Waiting for FastAPI to start..."
sleep 3

# Start Streamlit directly (not through Python)
echo "Starting Streamlit app..."
streamlit run streamlit_app.py

# When Streamlit is closed, also close FastAPI
echo "Shutting down FastAPI server..."
kill $FASTAPI_PID 2>/dev/null || true
