# LiveAsk

**Real-time Q&A and polls for presentations, running on Amazon EKS.**

The presenter shows a QR code. The audience asks and upvotes questions and answers polls from their phones, with no sign-up. The presenter's page and the projector screen update live over WebSockets, whichever Kubernetes pod each person happens to be connected to.

> **Status: in progress (3-day build).** The AWS/Kubernetes platform is done and validated; the LiveAsk app is being built now. Plan: [`TASKS.md`](TASKS.md) · Current state: [`CURRENT_STATE.md`](CURRENT_STATE.md) · Coding agents start at [`PROMPT_FOR_CODING_AGENT.md`](PROMPT_FOR_CODING_AGENT.md).

![LiveAsk architecture](docs/images/architecture.svg)

## Why it runs on Kubernetes (and not Lambda)

Live updates need **WebSocket connections that stay open for the whole talk**, from many phones at once. That suits a container that keeps connections in memory. My other project, the Say Coffee website, is serverless because its traffic is light and bursty. LiveAsk is on EKS because of its long-lived connections. I picked the platform for the workload.

## The interesting problem: real time across several pods

With 2–6 replicas, a phone connected to **pod A** posts a question, but the projector is connected to **pod B**. LiveAsk saves the question and calls `pg_notify` **in the same PostgreSQL transaction**. Every pod `LISTEN`s, so every pod pushes the event to its own WebSocket clients. No sticky sessions, no extra Redis. Details and trade-offs: [`ARCHITECTURE.md`](ARCHITECTURE.md).

## Kubernetes features used

| Object | Used for |
|---|---|
| Deployment (2+ replicas, spread across AZs) | API + WebSocket hub + pages; rolling updates with `maxUnavailable: 0` |
| initContainer | Database migrations under a Postgres advisory lock |
| Service + Ingress (ALB, target-type `ip`) | Traffic from the internet to pods; ALB idle timeout raised for WebSockets |
| ConfigMap / Secret | Limits and settings / database URL |
| Liveness + readiness probes, preStop hook | Zero-downtime deploys: drain, close sockets with code 1012, clients reconnect |
| HorizontalPodAutoscaler + metrics-server | Scale 2 → 6 pods under load (load test included) |
| PodDisruptionBudget | Keep a pod serving during node drains / Spot interruptions |
| CronJob | Nightly cleanup of rooms older than 24 h |
| StatefulSet + PVC (local only) | PostgreSQL with persistent storage on minikube; RDS on AWS |
| Namespace, security context | Isolation; non-root, read-only filesystem, no capabilities |

## AWS

Terraform (`infra/terraform/`): VPC across 2 AZs (public, private and isolated database subnets), **EKS** with Spot managed nodes and access entries, **AWS Load Balancer Controller** (IRSA), **RDS PostgreSQL** (password in Secrets Manager), **ECR**, **GitHub Actions OIDC** deploy role (no AWS keys in GitHub), **AWS Budgets** alerts. CI runs tests, image build, `terraform validate` and manifest rendering on every push.

## Run it

```bash
# Local, no AWS: Postgres + two app containers behind nginx (like two pods behind a load balancer)
docker compose up --build        # then open http://localhost:8000 in several tabs
# Kubernetes on your machine
minikube start -p eks-lab --driver=docker --memory=3072 --cpus=2 --addons=metrics-server,ingress
kubectl apply -k k8s/overlays/local
```

AWS (one session, ≈ USD 0.27/hour, about USD 1 for a 4-hour session; see [`SECURITY_AND_COST.md`](SECURITY_AND_COST.md)):

```bash
cd infra/terraform && cp terraform.tfvars.example terraform.tfvars   # fill in
terraform init && terraform apply
$(terraform output -raw kubeconfig_command) && cd ../.. && ./scripts/create-db-secret.sh
# then GitHub → Actions → "Deploy to EKS"
```

Teardown (always): `kubectl delete -k k8s/overlays/aws`, wait for the ALB to disappear, then `terraform destroy`.

> The Docker Compose command runs LiveAsk. Until day 2 is finished, the Kubernetes and AWS commands still use the placeholder notes manifests the platform was built and tested with.

## Roadmap

HTTPS on a custom domain · Cognito sign-in for presenters · NetworkPolicies · Argo CD (GitOps) · Prometheus/Grafana and autoscaling on connection count (KEDA) · Redis pub/sub comparison · separate staging/prod.

## Docs

[`PROJECT_REQUIREMENTS.md`](PROJECT_REQUIREMENTS.md) · [`ARCHITECTURE.md`](ARCHITECTURE.md) · [`DATABASE_DESIGN.md`](DATABASE_DESIGN.md) · [`API_SPECIFICATION.md`](API_SPECIFICATION.md) · [`SECURITY_AND_COST.md`](SECURITY_AND_COST.md) · [`DECISIONS.md`](DECISIONS.md) · [`TASKS.md`](TASKS.md)
