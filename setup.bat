@echo off
setlocal
rem ==========================================================================
rem  foc-masters-thesis - one-time setup on Windows
rem  Creates a virtual environment, installs the requirements, registers a
rem  Jupyter kernel and (optionally) records where the data folder is.
rem  Safe to run again: it reuses an existing .venv and just updates packages.
rem ==========================================================================

cd /d "%~dp0"

echo.
echo [1/4] Checking Python...
where python >nul 2>&1
if errorlevel 1 (
    echo   Python was not found. Install Python 3.10 or newer from python.org,
    echo   tick "Add python.exe to PATH" during install, then run this again.
    exit /b 1
)
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)"
if errorlevel 1 (
    echo   Python 3.10 or newer is required. Found:
    python --version
    exit /b 1
)
python --version

echo.
echo [2/4] Creating the virtual environment (.venv)...
if exist ".venv\Scripts\python.exe" (
    echo   .venv already exists - reusing it.
) else (
    python -m venv .venv || exit /b 1
)

echo.
echo [3/4] Installing requirements...
call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt || exit /b 1
python -m ipykernel install --user --name foc-masters-thesis --display-name "Python (foc-masters-thesis)" >nul
echo   Jupyter kernel registered as "Python (foc-masters-thesis)".

echo.
echo [4/4] Data folder
if defined THESIS_DATA (
    echo   THESIS_DATA is already set to: %THESIS_DATA%
) else (
    echo   The data is not part of the repo. Enter the full path to your
    echo   thesis-data folder, or press Enter to use the default in config\paths.py.
    set /p "DATA_PATH=  Path: "
)
if defined DATA_PATH (
    setx THESIS_DATA "%DATA_PATH%" >nul
    echo   Saved THESIS_DATA = %DATA_PATH%  ^(applies to new terminals^)
)

echo.
echo Setup complete. Next time, open a terminal in this folder and run:
echo     .venv\Scripts\activate
echo     python -m src.data_prep
echo.
endlocal