#!/usr/bin/env bash
# Applies the AWS overlay to the EKS cluster with the image the "Deploy to EKS" workflow pushed.
# Run it from a machine whose IP is in cluster_endpoint_public_access_cidrs, signed in to AWS
# (aws sso login), after `terraform apply` and scripts/create-db-secret.sh.
#
#   bash scripts/deploy-from-laptop.sh [git-sha]     # default: the tip of origin/main
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
tf() { terraform -chdir="$ROOT/infra/terraform" output -raw "$1"; }

SHA="${1:-$(git -C "$ROOT" rev-parse origin/main)}"
REGION="${AWS_REGION:-ap-southeast-1}"
IMAGE="$(tf ecr_repository_url):$SHA"
CLUSTER="$(tf cluster_name)"
NAMESPACE="$(tf app_namespace)"

aws ecr describe-images --region "$REGION" --repository-name "$(tf ecr_repository_url | cut -d/ -f2-)" \
  --image-ids "imageTag=$SHA" >/dev/null || { echo "No image tagged $SHA in ECR: run the Deploy to EKS workflow first." >&2; exit 1; }

aws eks update-kubeconfig --region "$REGION" --name "$CLUSTER" >/dev/null
echo "Cluster: $(kubectl config current-context)"

# The overlay names the image liveask:local; swap it for the pushed image in the rendered YAML.
kubectl kustomize "$ROOT/k8s/overlays/aws" | sed "s#image: liveask:local#image: $IMAGE#" | kubectl apply -f -
kubectl -n "$NAMESPACE" rollout status deployment/liveask --timeout=240s

for _ in $(seq 1 30); do
  host="$(kubectl -n "$NAMESPACE" get ingress liveask -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')"
  [ -n "$host" ] && { echo "App: http://$host"; exit 0; }
  sleep 10
done
echo "The load balancer has no address yet: kubectl -n $NAMESPACE describe ingress liveask" >&2
