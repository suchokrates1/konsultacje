# Deployment

This repository is set up for a simple production flow:

1. push to `main`
2. GitHub Actions runs tests and flake8
3. GitHub builds a Docker image and pushes it to `ghcr.io/suchokrates1/konsultacje`
4. GitHub connects to `minipc` through Tailscale and updates the running container

## GitHub secrets

Configure these repository secrets in GitHub:

- `TS_OAUTH_CLIENT_ID`: the same Tailscale OAuth client id already used by `retrievershop-suite`
- `TS_OAUTH_SECRET`: the same Tailscale OAuth secret already used by `retrievershop-suite`
- `SSH_PRIVATE_KEY`: private key that can SSH to `suchokrates1@100.110.194.46`

`GITHUB_TOKEN` is already used automatically for pushing the image from Actions to GHCR.
The deploy step assumes the GHCR package is public, so the server can pull it without a separate registry secret.

## Server preparation

Run these steps once on `minipc`:

```bash
hostname
cd /home/suchokrates1
git clone https://github.com/suchokrates1/konsultacje.git
cd /home/suchokrates1/konsultacje
cp .env.example .env
```

Fill `.env` with the real values. Do not commit it.

Then perform the first manual deployment:

```bash
export KONSULTACJE_IMAGE=ghcr.io/suchokrates1/konsultacje:latest
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
curl -fsS http://127.0.0.1:8080/healthz
```

## Runtime data

- secrets stay in `.env` on the server
- SQLite data persists in the Docker volume `konsultacje-instance`
- the DOCX template remains in the image because `app/static/wzor.docx` is committed to the repository

## Updating production

After the initial setup, each push to `main` should be enough. The workflow will:

- pull the latest repo on the server
- pull the exact image built for the current commit
- recreate the container with `docker compose -f docker-compose.prod.yml up -d`
- verify the app using `http://127.0.0.1:8080/healthz`