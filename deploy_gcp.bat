@echo off
echo ============================================================
echo  ALTAIR: GCP Cloud Build and Cloud Run Deployer (asia-south1)
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
echo [*] Deploying image to Google Cloud Run locally...
call %GCLOUD_BIN% run deploy altair-service ^
  --image asia-south1-docker.pkg.dev/%PROJECT_ID%/papertrade-repo/altair-app:latest ^
  --region asia-south1 ^
  --platform managed ^
  --allow-unauthenticated ^
  --set-env-vars UPSTOX_ACCESS_TOKEN=eyJ0eXAiOiJKV1QiLCJrZXlfaWQiOiJza192MS4wIiwiYWxnIjoiSFMyNTYifQ.eyJzdWIiOiI1TkNKUVgiLCJqdGkiOiI2YTgwMTQwYzUzNzUwMDQzMDU3MGJkMTYiLCJpc011bHRpQ2xpZW50IjpmYWxzZSwiaXNQbHVzUGxhbiI6ZmFsc2UsImlzRXh0ZW5kZWQiOnRydWUsImlhdCI6MTc4Njc3ODYzNiwiaXNzIjoidWRhcGktZ2F0ZXdheS1zZXJ2aWNlIiwiZXhwIjoxODE4MzY3MjAwfQ.tId882rzxtNv7drIGs687mhxU-jUCx4U6W7F0wwXjSg,AUTH_USER=Aditya.raj,AUTH_PASS=Aditya@3205#,SUPABASE_URL=https://mgmojigurnojkwqdzgtv.supabase.co,SUPABASE_KEY=sb_publishable_qK6A9P7JDZ4PR7pmN3G5yw_mRgVqd4I,SUPABASE_DB_URL=postgresql://postgres.mgmojigurnojkwqdzgtv:QLA@3205#aditya@aws-0-ap-south-1.pooler.supabase.com:6543/postgres

if %ERRORLEVEL% neq 0 (
    echo [!] Cloud Run deployment failed.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [+=] SUCCESS! ALTAIR Engine successfully deployed to Google Cloud Run!
echo.
pause
