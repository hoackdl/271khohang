@echo off


REM Kích hoạt virtual environment
SET "VENV_PATH=E:\My Drive\Python Web\XML\271khohang\venv"
CALL "%VENV_PATH%\Scripts\activate.bat"

REM Folder chứa file XML
SET "INVOICE_DIR=E:\My Drive\DT-CP\HD_VAO\THU"

REM Script Python
SET "SCRIPT_PATH=E:\My Drive\Python Web\XML\271khohang\scripts\upload_invoices_cron.py"

REM Log file
SET "LOG_FILE=E:\My Drive\Python Web\XML\271khohang\scripts\upload_cron.log"

echo %DATE% %TIME% >> "%LOG_FILE%"

REM Chạy Python script, truyền folder XML
python "%SCRIPT_PATH%" "%INVOICE_DIR%" >> "%LOG_FILE%" 2>&1

echo Done! Press any key to exit...
pause
