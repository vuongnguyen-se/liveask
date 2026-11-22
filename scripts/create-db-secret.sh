#!/usr/bin/env bash
# Reads the RDS password from Secrets Manager and stores DATABASE_URL as a
# Kubernetes Secret in the app namespace. Run after `terraform apply` and
# `aws eks update-kubeconfig`. The password never touches disk or git.
set -euo pipefail

TF_DIR="$(dirname "$0")/../infra/terraform"
tf() { terraform -chdir="$TF_DIR" output -raw "$1"; }

DB_HOST="$(tf db_endpoint)"
SECRET_ARN="$(tf db_secret_arn)"
NAMESPACE="$(tf app_namespace)"

SECRET_JSON="$(aws secretsmanager get-secret-value --secret-id "$SECRET_ARN" --query SecretString --output text)"

DATABASE_URL="$(SECRET_JSON="$SECRET_JSON" DB_HOST="$DB_HOST" python3 -c '
import json, os, urllib.parse as u
s = json.loads(os.environ["SECRET_JSON"])
print("postgresql://%s:%s@%s:5432/liveask?sslmode=require" % (
    u.quote(s["username"], safe=""), u.quote(s["password"], safe=""), os.environ["DB_HOST"]))
')"

kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -
kubectl -n "$NAMESPACE" create secret generic liveask-db \
  --from-literal=DATABASE_URL="$DATABASE_URL" \
  --dry-run=client -o yaml | kubectl apply -f -

echo "Secret liveask-db is in namespace $NAMESPACE. Restart pods to pick it up:"
echo "  kubectl -n $NAMESPACE rollout restart deployment/liveask"
