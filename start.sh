#!/bin/bash
echo "======================================================================="
echo "Starting Home Credit LAP AI Voice Agent Server"
echo "======================================================================="
echo ""

python3 -m pip install -r backend/requirements.txt
echo ""
echo "Starting Web Server and Voice Simulator at http://localhost:8000 ..."
python3 backend/run_server.py
