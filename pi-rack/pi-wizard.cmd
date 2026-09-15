@echo off
REM pi-rack setup wizard - the front door.
REM
REM   pi-wizard              guided flow
REM   pi-wizard doctor       check this machine can do the job
REM   pi-wizard plan         validate fleet.toml
REM   pi-wizard flash NODE   write a card, end to end
REM   pi-wizard seed NODE    write only the cloud-init files to an already-written card
REM
REM Writing a card needs Administrator. Seeding one does not - which is why the
REM fallback (write with the Raspberry Pi Imager GUI, then `pi-wizard seed NODE`)
REM always works.

setlocal
set "PIRACK_ROOT=%~dp0"
pushd "%PIRACK_ROOT%wizard"

where python >nul 2>nul
if errorlevel 1 (
    echo.
    echo   Python was not found on PATH.
    echo   piwiz needs Python 3.11 or newer ^(it uses tomllib^).
    echo.
    popd
    endlocal
    exit /b 1
)

python -m piwiz %*
set "RC=%ERRORLEVEL%"

popd
endlocal & exit /b %RC%
