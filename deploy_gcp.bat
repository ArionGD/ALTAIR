@echo off
echo ============================================================
echo  ALTAIR: GCP Cloud Build & Cloud Run Deployer (asia-south1)
echo ============================================================
echo.

set GCLOUD_BIN="C:\Users\adity\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"
set PROJECT_ID=project-ba753270-5762-47c5-ba6

echo [*] Setting active GCP Project to: %PROJECT_ID%
call %GCLOUD_BIN% config set project %PROJECT_ID%
if %ERRORLEVEL% neq 0 (
    echo [!] Error setting GCP project. Please verify gcloud installation and credentials.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [*] Submitting build to Google Cloud Build...
call %GCLOUD_BIN% builds submit --config cloudbuild.yaml
if %ERRORLEVEL% neq 0 (
    echo [!] Cloud Build failed.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [+=] SUCCESS! ALTAIR Engine successfully deployed to Google Cloud Run!
echo.
pause
