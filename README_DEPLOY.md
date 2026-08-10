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

GitHub + Render automated deploy (recommended):

1. Create a GitHub repository and push this project (see commands below).
2. In the GitHub repo, add two repository secrets: `RENDER_API_KEY` and `RENDER_SERVICE_ID`.
	- `RENDER_API_KEY`: your Render API key (Account -> API Keys)
	- `RENDER_SERVICE_ID`: the Render service id for the web/worker service you want to trigger
3. The included workflow `.github/workflows/deploy_render.yml` will call the Render API to start a deploy on push to `main`/`master`.

Push commands (run from project root):

```bash
git remote add origin <your-github-repo-url>
git branch -M main
git push -u origin main
```

Once pushed and secrets set, pushes to `main` will trigger Render deploys automatically.

GitHub Actions CI:

- A basic CI workflow is included at `.github/workflows/ci.yml` to run syntax checks and tests.
