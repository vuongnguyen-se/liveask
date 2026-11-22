# Resume on another computer

Everything you need to continue LiveAsk from a clean machine. Read `CURRENT_STATE.md` for what is built and verified, and `TASKS.md` for the board. Written 2026-11-22.

## 0. Where the work is

All work (Day 1, the UI track and Day 2) is on **`main`**: it was merged through PR #1 on 2026-11-22. Branch off `main` for new work.

```powershell
git clone https://github.com/vuongnguyen-se/liveask.git
cd liveask
```

**PR #1** (https://github.com/vuongnguyen-se/liveask/pull/1) is merged, and **GitHub CI is green** on the PR and on `main` (all three jobs). CI runs on pushes to `main`, on pull requests and by hand; the deploy workflow (`deploy.yml`) has still never run.

Not in git on purpose (recreate them): `.venv/`, `e2e/node_modules/`, `infra/terraform/.terraform/`, `infra/terraform/terraform.tfvars` (it holds your email and IP), `shots/`, `.taste-skill/chrome-check`. Nothing secret is in git.

## 1. Install (once)

| Tool | Why | Check |
|---|---|---|
| Git | the repo | `git --version` |
| Python 3.13 | the app and its tests | `python --version` |
| Docker Desktop | Compose and minikube's driver (**start it before anything else**) | `docker info` |
| Node 22 or newer | the browser checks in `e2e/` | `node --version` |
| Edge or Chrome | the browser checks drive it (no download); other path: set `BROWSER_PATH` | |
| kubectl | Kubernetes | `kubectl version --client` |
| minikube | local cluster | `minikube version` |
| Terraform 1.6 or newer | AWS infrastructure (Day 3) | `terraform version` |
| AWS CLI 2 | Day 3 | `aws --version` |
| gh CLI (optional) | GitHub | `gh auth status` |

Windows: `winget install Git.Git Python.Python.3.13 Docker.DockerDesktop OpenJS.NodeJS Kubernetes.kubectl Kubernetes.minikube Hashicorp.Terraform Amazon.AWSCLI GitHub.cli`. Open a **new** terminal afterwards so the tools are on PATH. Commands below are PowerShell; Git Bash works too (see the note at the end).

## 2. Set up and check that it works (about 10 minutes, USD 0)

```powershell
cd liveask                                   # the repo folder
python -m venv .venv
.venv\Scripts\python -m pip install -r app/requirements-dev.txt
docker compose up -d db                      # Postgres on 127.0.0.1:5432
$env:TEST_DATABASE_URL = "postgresql://liveask:liveask-local-only@127.0.0.1:5432/liveask"
cd app; ..\.venv\Scripts\python -m pytest -q; cd ..     # expect: 108 passed
.venv\Scripts\python -m ruff check app                   # expect: All checks passed

docker compose up --build -d                 # Postgres + migrate + 2 app containers + nginx
# open http://localhost:8000  (port 8080 may be taken on the old computer; set LIVEASK_PORT to change)
cd e2e; npm install; npm run all             # expect: 19 PASS (run.js) and 6 PASS (reconnect.js)
node a11y.js                                 # expect: 8 PASS
```

If a port is busy, `docker compose down` and retry, or `$env:LIVEASK_PORT = "9000"` (then `BASE_URL=http://localhost:9000`).

## 3. Kubernetes on minikube (optional, USD 0)

```powershell
minikube start -p eks-lab --driver=docker --memory=3072 --cpus=2 --addons=metrics-server,ingress
minikube image build -p eks-lab -t liveask:local app
kubectl apply -k k8s/overlays/local
kubectl -n liveask get pods                  # expect: 2 liveask pods + postgres-0, all Running
minikube tunnel -p eks-lab                   # leave it running; the app is on http://127.0.0.1
# in another terminal:
cd e2e; $env:BASE_URL = "http://127.0.0.1"; node run.js; node rollout.js
```

Stop everything when done: `minikube stop -p eks-lab; docker compose stop`.

## 4. Day 3: the AWS session 💰

Nothing has been applied to AWS. The session costs about **USD 0.27 per hour** (about USD 1 for 4 hours) and **always ends with the teardown**. Do not leave it running: left on for a month it is about USD 190. Rules: `SECURITY_AND_COST.md`.

1. **Sign in:** `aws sso login --profile clouddocs-dev` (if that is the same account) or `aws login`, then `aws sts get-caller-identity`. Region `ap-southeast-1`.
2. **Check Kubernetes 1.35 is in standard support** on EKS: `aws eks describe-cluster-versions --region ap-southeast-1` (see `CURRENT_STATE.md`).
3. **Configure Terraform:** `cd infra/terraform; copy terraform.tfvars.example terraform.tfvars`, then fill in `owner` (your GitHub handle), `github_repo` (`vuongnguyen-se/liveask`), `budget_email`, and uncomment `cluster_endpoint_public_access_cidrs` with your public IP (`curl https://checkip.amazonaws.com`, then `["x.x.x.x/32"]`). Leave `create_github_oidc_provider` out (an OIDC provider already exists in the account). Check whether new IAM roles need Say Coffee's permissions boundary.
4. **Review:** `terraform init`, `terraform plan`; read it.
5. **💰 Apply (ask before this, say the cost):** `terraform apply`. Then `aws eks update-kubeconfig ...` (the command is a Terraform output), `scripts/create-db-secret.sh`, set the GitHub variables, run the **Deploy to EKS** workflow (it pushes the image), then `bash scripts/deploy-from-laptop.sh` from your laptop to apply the manifests (the API is locked to your IP, so GitHub runners cannot). Also set `github_oidc_repo_claim` in `terraform.tfvars` if the repository uses immutable OIDC subjects (`CURRENT_STATE.md` section 7). Done when the ALB URL works from a phone.
6. **Prove it on EKS:** `BASE_URL=http://<alb> node e2e/run.js`, `node e2e/rollout.js`, `python scripts/load_test.py --base http://<alb> --clients 200 --burn-workers 6`; screenshots of `kubectl get pods -o wide` (AZ spread), the HPA, the ALB target group, and the app on a phone. This is where the **latency target (p95 under 1 s)** gets its real measurement.
7. **🧹 Teardown, every time:** `kubectl delete -k k8s/overlays/aws`, wait until the ALB is gone (EC2, Load balancers), then `cd infra/terraform; terraform destroy`. Then check tag `Project=liveask`: no EKS cluster, EC2, NAT gateway, Elastic IPs, load balancers, RDS or EBS left. Next day look at Cost Explorer.
8. Update `README.md` with the EKS numbers and screenshots, and `CURRENT_STATE.md` / `TASKS.md` (D3-03 to D3-07).

The CI workflow is green; the **deploy workflow has never run**. It assumes `main`, where the work now is.

## 5. If you use an AI coding agent

Open the repo and tell it: *"Read `PROMPT_FOR_CODING_AGENT.md`, `CURRENT_STATE.md`, `AI_CODING_RULES.md` and `TASKS.md`, then continue with Day 3."* The rules in `AI_CODING_RULES.md` (small commits, ask before anything that costs money, never push without asking) apply. The UI design skill is only needed to re-vendor or re-check the landing page (`docs/ui/KIT.md`); the kit is already in the repo.

## 6. Known gotchas

- **Windows:** use `127.0.0.1`, not `localhost`, in `DATABASE_URL` for the async driver. In Git Bash, `MSYS_NO_PATHCONV=1` for commands that pass Unix paths into containers. `python -m liveask.run` is the Windows dev server.
- **Not Windows:** the same commands work; use `.venv/bin/python` and `source`, and set `BROWSER_PATH` if Chrome is somewhere unusual. `uvicorn liveask.main:app` runs the app directly on Linux and macOS.
- Another project on the old computer used port 8080; LiveAsk uses 8000.
- Long shell commands with large heredocs sometimes fail to parse in Git Bash: put the content in a file instead.
- `terraform apply` needs AWS credentials; `kubectl` talks to whichever context is current: check `kubectl config current-context` (`eks-lab` for minikube) before applying anything.
- Open items and honest limits: `CURRENT_STATE.md` sections 4 and 7 (the p95 latency, Vietnamese letters, unlimited room creation, one open UI gate finding).
