# Deploy GENESIS to Hugging Face Spaces (Docker)

This project is already structured for a Docker Space using:

- `Dockerfile` (build + run backend)
- `openenv.yaml` (OpenEnv/FastAPI metadata)
- `server.app:app` on port `7860`

## 1) Create the Space

1. Go to https://huggingface.co/new-space.
2. Choose:
   - **Space SDK:** Docker
   - **Space name:** your choice (for example: `genesis-env`)
   - **Visibility:** Public or Private
3. Click **Create Space**.

## 2) Push this repository to the Space remote

From this repository root:

```bash
git remote add space https://huggingface.co/spaces/<YOUR_USERNAME>/<YOUR_SPACE_NAME>
git push space main
```

If your default branch is not `main`, push your active branch:

```bash
git push space HEAD:main
```

## 3) Watch the build logs

In the Hugging Face Space page:

1. Open **Logs**.
2. Wait for Docker build completion.
3. Confirm the app starts and responds on `/health`.

Expected health response:

```json
{"status":"ok"}
```

## 4) Optional environment variables / secrets

Set these in Space **Settings -> Variables and secrets** only if needed:

- `GENESIS_SOLANA_RPC_URL`
- `GENESIS_SOLANA_PROGRAM_ID`
- `GENESIS_SOLANA_KEYPAIR_JSON`
- `GENESIS_SOLANA_COMMITMENT`

The Solana proof path is optional. The server runs without these values.

## 5) Verify endpoints after deploy

- `https://huggingface.co/spaces/<YOUR_USERNAME>/<YOUR_SPACE_NAME>`
- `https://<your-space-subdomain>.hf.space/health`
- `https://<your-space-subdomain>.hf.space/mcp`

## Notes

- This Docker setup deploys the **backend service** (FastMCP/FastAPI).
- Frontend (`frontend/`) can be deployed separately (for example Vercel) and pointed at your Space URL via `NEXT_PUBLIC_GENESIS_URL`.
- `.dockerignore` excludes heavy local artifacts to keep Space builds faster and more stable.

## Troubleshooting

- Build fails with dependency/import errors:
  - Rebuild after pulling the latest commit.
  - Check Space logs for the first failing package/import.
- App boots but UI cannot connect:
  - Ensure frontend is calling the correct Space base URL.
  - Confirm `/health` works before testing `/mcp`.
- Push rejected with auth error:
  - Use a Hugging Face token with write access.
  - Re-run Git credential setup and push again.
