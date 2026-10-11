@echo off
echo =======================================================================
echo Starting Home Credit LAP AI Voice Agent Server
echo =======================================================================
echo.

python -m pip install -r backend/requirements.txt
echo.
echo Launching Server...
echo Opening in your browser: http://localhost:8000
echo.
python backend/run_server.py
pause
