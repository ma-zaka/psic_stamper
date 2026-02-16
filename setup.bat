@echo off
echo Setting up PDF Stamper environment...

:: Use Anaconda Python
set PYTHON_EXE=C:\Users\maliz\anaconda3\python.exe

:: Create virtual environment if it doesn't exist
if not exist "venv" (
    echo Creating virtual environment...
    "%PYTHON_EXE%" -m venv venv
    if errorlevel 1 (
        echo Error: Failed to create virtual environment
        pause
        exit /b 1
    )
)

:: Activate virtual environment and install packages
echo Installing required packages...
call venv\Scripts\activate.bat
"%PYTHON_EXE%" -m pip install --upgrade pip
"%PYTHON_EXE%" -m pip install -r requirements.txt

:: Create the db_manager.py file if it doesn't exist
if not exist "db_manager.py" (
    echo Creating database manager module...
    copy /y NUL db_manager.py >NUL
    echo Please copy the database manager code to db_manager.py
)

:: MongoDB setup instructions
echo.
echo -----------------------------------------------------
echo MongoDB Setup Instructions:
echo 1. Download and install MongoDB Community Server from:
echo    https://www.mongodb.com/try/download/community
echo 2. Start MongoDB service
echo 3. Make sure MongoDB is running on localhost:27017
echo 4. Run the following command to setup the database:
echo    mongosh --file setup_db.js
echo -----------------------------------------------------
echo.

:: Deactivate virtual environment
call venv\Scripts\deactivate.bat

echo Setup completed successfully!
echo You can now run the application using run_pdf_stamper.bat
pause