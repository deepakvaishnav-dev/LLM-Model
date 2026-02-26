@echo off
echo Starting the Backend Server...
call venv\Scripts\activate.bat
uvicorn app.main:app --reload
