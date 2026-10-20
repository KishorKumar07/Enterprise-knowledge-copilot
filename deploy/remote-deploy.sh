#!/usr/bin/env bash
# Runs ON the EC2 app server (as root, via AWS SSM) to roll out one release.
#
#   usage: remote-deploy.sh <image-tag> <ecr-registry>
#
# Layout on the server:
#   /opt/apps/ekc/repo/                git checkout of this repo, pinned to the release SHA
#   /opt/apps/ekc/.env                 secrets, chmod 600, created once by hand (never in git)
#   /opt/apps/ekc/docker-compose.yml   copied from deploy/docker-compose.prod.yml
#   /opt/apps/ekc/observability/       copied from the repo (Prometheus + Grafana config)
#
# The server never builds anything: it only pulls images that CI already pushed.
set -euo pipefail

TAG="${1:?usage: remote-deploy.sh <image-tag> <ecr-registry>}"
REGISTRY="${2:?usage: remote-deploy.sh <image-tag> <ecr-registry>}"
REGION="${AWS_REGION:-ap-south-1}"
APP_DIR=/opt/apps/ekc
REPO_DIR="$APP_DIR/repo"

[ -f "$APP_DIR/.env" ] || { echo "missing $APP_DIR/.env - create it first (see the deployment plan)" >&2; exit 1; }

echo "== sync deploy files (release $TAG) =="
cp "$REPO_DIR/deploy/docker-compose.prod.yml" "$APP_DIR/docker-compose.yml"
mkdir -p "$APP_DIR/observability"
cp -r "$REPO_DIR/observability/." "$APP_DIR/observability/"

cd "$APP_DIR"
export ECR_REGISTRY="$REGISTRY" IMAGE_TAG="$TAG"

# PUBLIC_URL and the Grafana/Postgres passwords come from .env; compose reads it.
echo "== log in to ECR and pull =="
aws ecr get-login-password --region "$REGION" \
  | docker login --username AWS --password-stdin "$REGISTRY"
docker compose pull backend frontend

# Migrations are a discrete step, run BEFORE the new containers start, never in
# the container's CMD: a restart must not re-run them, and a failed migration
# should fail the deploy loudly instead of crash-looping a container.
echo "== database up, then migrate =="
docker compose up -d --wait postgres
docker compose run --rm --no-deps backend alembic upgrade head

echo "== start release $TAG =="
docker compose up -d --remove-orphans

echo "== wait for the app to answer locally =="
for i in $(seq 1 30); do
  if curl -fsS http://127.0.0.1:7860/api/health >/dev/null && curl -fsS -o /dev/null http://127.0.0.1:3100/login; then
    echo "healthy after $((i * 5))s"
    docker image prune -f >/dev/null || true
    docker compose ps
    exit 0
  fi
  sleep 5
done

echo "release $TAG did not become healthy" >&2
docker compose ps >&2 || true
docker compose logs --tail 40 backend >&2 || true
exit 1
