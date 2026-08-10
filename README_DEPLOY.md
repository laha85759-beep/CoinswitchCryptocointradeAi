# Deployment guide

This guide shows recommended deployment steps for running the bot and UI 24/7.

Recommended option: NSSM on Windows (service), plus Render for cloud hosting of UI + worker.

Local Windows (NSSM):

1. Install NSSM: https://nssm.cc/download
2. Run the script:

```powershell
cd cs_bot_v2\scripts
powershell -ExecutionPolicy Bypass -File install_nssm_service.ps1
```

Render (cloud):

1. Connect your GitHub repo to Render.
2. Add `render.yaml` to the repo root (already included).
3. Set environment variables in Render (CS_API_KEY, CS_API_SECRET, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, DELTA_API_KEY, DELTA_API_SECRET).

GitHub Actions CI:

- A basic CI workflow is included at `.github/workflows/ci.yml` to run syntax checks and tests.
