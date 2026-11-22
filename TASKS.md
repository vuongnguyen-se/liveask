# LiveAsk Task Board (3-day plan)

The single place to track progress. Tick a box only when its **Done when** check has really passed, and add the date. Decisions `D-xxx` are in `DECISIONS.md`.

Legend: `[ ]` todo · `[~]` in progress · `[x]` done · `[-]` dropped (say why) · 💰 creates billable AWS resources (ask first) · 🧹 includes teardown

## Progress overview

| Day | Goal | Status |
|---|---|---|
| 0 | Platform skeleton (Terraform, K8s, CI) carried over into the fresh `liveask` repo | ✅ Done (2026-11-21) |
| 1 | The app: rooms, questions, votes, polls, real-time across pods; runs in Docker Compose | ✅ Done (2026-11-21) |
| UI | Redesign the UI with taste-skill (landing page + three app views), one commit per component | 🔨 In progress (D-016 to D-018 accepted) |
| 2 | Kubernetes on minikube: all objects, cross-pod real time, zero-downtime update, HPA demo | Not started |
| 3 | One AWS session on EKS, screenshots, teardown; README and diagram final | Not started |

---

## Day 1: The app (local, USD 0)

- [x] **D1-01** (2026-11-21) Restructure `app/` into the `liveask` package (see `ARCHITECTURE.md` §6). `config.py` (env vars), `db.py` (psycopg async pool), `schema.sql`, `migrate.py` with `pg_advisory_lock`. Remove the notes endpoints but keep `/healthz` and the `/burn` load helper.
  - Done when: `python -m liveask.migrate` runs twice against Compose Postgres without errors; tests pass.
- [x] **D1-02** (2026-11-21) Rooms: `POST /api/rooms`, `GET /api/rooms/{code}`, `POST /api/rooms/{code}/close`; code generator; host token hashing; tests.
  - Done when: tests cover create, get, wrong token → 403, and that the token is not stored in plain text.
- [x] **D1-03** (2026-11-21) Questions and votes: create (rate limit), toggle vote (counter updated in the same transaction), host moderation; tests.
  - Done when: tests cover one-vote-per-device, unvote, hidden questions not visible to the audience, and 429.
- [x] **D1-04** (2026-11-21) Polls: create, open/close, vote, change vote, counts; tests.
- [x] **D1-05** (2026-11-21) Real time: `hub.py` with one LISTEN connection per process; every write calls `pg_notify` in its transaction; `/ws/rooms/{code}` with hello/ping/pong; `/readyz` checks the DB and the LISTEN connection.
  - Done when: an integration test (or script) starts **two app processes** on different ports against the same Postgres; a question posted to process A arrives on a WebSocket connected to process B.
- [x] **D1-06** (2026-11-21) Pages: `/`, `/r/{code}`, `/host/{code}#t=…`, `/screen/{code}` in plain HTML/CSS/JS; device UUID in `localStorage`; reconnect with backoff + resync; QR code on the screen view (small JS library vendored into `static/`, no CDN); show "connected to pod …".
  - Done when: in a browser, three tabs (audience, host, screen) update each other live.
- [x] **D1-07** (2026-11-21) `docker-compose.yml`: postgres + migrate + **two** api containers behind a tiny nginx (round robin) to mimic two pods.
  - Done when: `docker compose up --build`, open the site through nginx, and tabs on different containers update each other.

## UI track: redesign with taste-skill (after Day 1, before Day 2; time-box about half a day)

Source: `C:\Users\Vuong\Downloads\taste-skill` (tasteskill 2.5.1, also linked as `~/.claude/skills/design-taste-frontend`). Decisions: D-016 to D-018 (accepted). Git rules: `AI_CODING_RULES.md` section 7 (one commit per component, Conventional Commits). UI rules: section 8.

How the skill applies: it builds company and product websites. Its **full workflow and finish gate** run on the **landing page `/`** (kind: software). The **audience, host and screen** views use its design system (tokens, type, radius, buttons, contrast, accessibility) but not its marketing-page rules.

Stop rule: if the gate still fails after 3 rounds, report the open FAILs (the skill's own rule) and move on. At about half a day, stop and start D2-01.

- [x] **UI-00 Safety net first.** (2026-11-21) Move the browser checks into the repo so every UI commit can be verified.
  - [x] `test(e2e)`: `e2e/` with `package.json` (dev only, `playwright-core`), the three-view check (19 checks), runnable against Compose on `:8000` and against two local pods; browser path from `BROWSER_PATH`
  - [x] `test(e2e)`: the reconnect check (kill and restart a pod)
  - [x] `docs(e2e)`: how to run it (Windows and Git Bash)
  - Done when: `node e2e/run.js` passes against `docker compose up` and `pytest` is unchanged.
- [x] **UI-01 Brief, copy, plan and deal** (documents only, `docs/ui/DESIGN_PLAN.md`). Written and approved 2026-11-21.
  - [x] fact sheet and voice card; page kind `software`; the main action word for word ("Create a room")
  - [x] all landing copy written first and checked with `copy-lint.mjs`
  - [x] page plan by screens and the deal (hero, palette, type pairing, nav, footer, close, rhythm, buttons, mark), each with a one-line reason
  - Done when: `copy-lint` has no FAIL and you approve the plan.
- [x] **UI-02 Foundation.** (2026-11-21)
  - [x] `chore(ui)`: vendor the kit core, unmodified, into `app/liveask/static/assets/`; `.gitignore` the gate's scratch files in `.taste-skill/`, keep `waivers.json`
  - [x] `feat(ui)`: self-host the two dealt font faces (woff2) with `@font-face` and `font-display: swap`
  - [x] `feat(ui)`: the dealt `:root` tokens, shared by all four pages
  - [x] `test(ui)`: guard test exempts the kit by path only; image still builds; report the image size change
  - Done when: `pytest` green, the Docker image builds and runs, no request leaves localhost.
- [x] **UI-03 Landing page `/`** (2026-11-22; **`GATE: OPEN`**: 1 finding open, `ui-centre` on the hero window, and 3 `section-gaps` waivers at 390 px, see `CURRENT_STATE.md`) (kind: software; the full skill workflow; one commit per section).
  - [ ] `feat(landing)`: nav and hero; the **create-room** and **join-by-code** actions still work
  - [ ] `feat(landing)`: `app-frame` showing LiveAsk's own UI as live HTML
  - [ ] `feat(landing)`: feature sections (live across pods, host controls and polls, projector view)
  - [ ] `feat(landing)`: how-it-works diagram card (pods, Postgres `NOTIFY`)
  - [ ] `feat(landing)`: FAQ and closing footer
  - [ ] `test(landing)`: `copy-lint`, `consistency`, `check`, `perf`, then `gate.mjs`; waivers listed with reasons
  - Done when: `GATE: PASS` (or `OPEN` with every waiver and open FAIL reported) and the e2e check can still create and join a room.
- [x] **UI-04 Audience view** (phone first, 390 px).
  - [x] `style(audience)`: header and connection pill
  - [x] `style(audience)`: ask form (counter, errors under the field, 44 px controls)
  - [x] `style(audience)`: question card and upvote control
  - [x] `style(audience)`: poll card with live bars
  - [x] `style(audience)`: closed, empty and not-found states
  - Done when: e2e passes; no sideways scroll at 320 px; every control at least 44 px.
- [x] **UI-05 Host console.**
  - [x] `style(host)`: share panel and close-room action
  - [x] `style(host)`: poll composer and poll controls
  - [x] `style(host)`: question list with moderation actions
  - Done when: e2e passes; hide, reopen, answer and close still work.
- [x] **UI-06 Projector screen** (1280x720 and 1920x1080).
  - [x] `style(screen)`: QR and code panel
  - [x] `style(screen)`: top questions, readable from the back of a room (large type, 7:1 contrast)
  - [x] `style(screen)`: live poll bars
  - Done when: screenshots at both sizes read well and e2e passes.
- [~] **UI-07 Review and ship.** (2026-11-22; done except GitHub CI, which cannot run until the branch is pushed)
  - [x] accessibility pass: contrast, keyboard order, focus ring, reduced motion, light and dark
  - [x] responsive screenshots (1440, 1024, 768, 390) saved to `docs/images/`
  - [x] `docs`: README screenshots and `CURRENT_STATE.md` updated
  - Done when: `pytest`, `ruff`, e2e and CI are green, and the branch is merged with `--no-ff`.

## Day 2: Kubernetes on minikube (USD 0)

- [x] **D2-01** `k8s/base`: rename everything from `notes` to `liveask`; ConfigMap; Deployment with **initContainer `migrate`**, probes, **preStop sleep 10**, `terminationGracePeriodSeconds: 45`, `maxUnavailable: 0`; Service; HPA; PDB; **CronJob `liveask-cleanup`** (`concurrencyPolicy: Forbid`). (2026-11-22) Verified on minikube: 2 pods Ready, migrate initContainer, probes, preStop, rollout restart.
- [x] **D2-02** `k8s/overlays/local`: **Postgres StatefulSet** + headless Service + `volumeClaimTemplates` (PVC); `secretGenerator` for local creds; Ingress for the minikube `ingress` addon. (2026-11-22) Verified: 2 Ready app pods, 1 Ready postgres pod; deleting `postgres-0` kept the data. Found and fixed: the overlay's own objects landed in `default` until the overlay set `namespace: liveask`.
  - Done when: `kubectl apply -k k8s/overlays/local` gives 2 Ready app pods and 1 Ready postgres pod; deleting the postgres pod keeps the data (PVC).
- [x] **D2-03** Cross-pod demo: through the Ingress, open tabs until they show **different pod names**; real time still works between them. (2026-11-22) `e2e/run.js` 19/19 on minikube behind ingress-nginx, host and screen on different pods.
- [x] **D2-04** Zero-downtime demo (`scripts/rolling-update-demo.sh`): keep the screen open, run `kubectl rollout restart deployment/liveask`; clients reconnect automatically, nothing is lost. Record a short GIF or screenshots. (2026-11-22) `e2e/rollout.js` 6/6: 32 of 32 questions stored, replicas never below 2, the screen reconnected to a new pod and caught up. No GIF recorded.
- [x] **D2-05** Load test (`scripts/load_test.py`): open N WebSockets + post questions/votes; watch `kubectl get hpa,pods -w` scale up. Save a screenshot. (2026-11-22) 200 clients over 6 pods, 18,400 of 18,400 delivered, HPA 2 to 4 to 6 pods at CPU 345%/60%. p95 latency about 1.1 s is dominated by the Windows tunnel (POST median 290 ms): re-measure on EKS. No screenshot saved; the output is in `CURRENT_STATE.md`.
- [x] **D2-06** Run the CronJob manually (`kubectl create job --from=cronjob/liveask-cleanup …`) with an expired test room; it gets deleted. (2026-11-22) Manual job logged "removed 1 expired room"; 0 left.
- [~] **D2-07** Update CI: tests for the new package, image build, kustomize render for both overlays. Update `scripts/create-db-secret.sh` (secret `liveask-db`, namespace `liveask`, db `liveask`). Done in code (2026-11-22): `ci.yml` runs ruff, pytest with a Postgres service, the image build and a render of both overlays; the secret script, load test and deploy workflow are renamed. **CI has not run on GitHub: nothing was pushed.**
  - Done when: CI green.

## Day 3: AWS session on EKS 💰 🧹 (≈ 3–4 h, ≈ USD 1)

Before starting: `aws login` (or SSO profile), `terraform.tfvars` filled in, check `kubernetes_version` is in standard support (`aws eks describe-cluster-versions`).

- [x] **D3-01** Terraform edits (no apply yet): RDS `db_name`/`username` → `liveask`, access entry namespace → `liveask`; `terraform fmt`/`validate`; review `terraform plan`. (2026-11-22) Renames done; `fmt`, `init -backend=false` and `validate` pass. `terraform plan` not reviewed (needs AWS sign-in).
- [x] **D3-02** Ingress for ALB: `alb.ingress.kubernetes.io/load-balancer-attributes: idle_timeout.timeout_seconds=3600`, `target-group-attributes: deregistration_delay.timeout_seconds=30`, health check `/readyz`. (2026-11-22) Annotations added; both overlays render. Not yet seen on a real ALB.
- [ ] **D3-03** 💰 `terraform apply`; `aws eks update-kubeconfig`; `scripts/create-db-secret.sh`; set GitHub variables; run **Deploy to EKS**.
  - Done when: the ALB URL works from a phone; two phones on mobile data plus a laptop update live.
- [ ] **D3-04** Repeat the D2-03/04/05 demos on EKS; screenshots of pods spread across AZs (`kubectl get pods -o wide`), HPA scaling, the ALB target group, and the app on a phone.
- [ ] **D3-05** (Optional, if time) HTTPS: ACM certificate + Route 53 record `ask.vuongdomain.click`, Ingress `certificate-arn` + `ssl-redirect`.
- [ ] **D3-06** 🧹 Teardown per `SECURITY_AND_COST.md` §3. Next day: confirm in Cost Explorer.
- [ ] **D3-07** Final README: what it is, screenshots/GIF, architecture diagram, the "why containers" and "multi-pod fan-out" explanations, K8s objects table, how to run locally, real cost of the session, roadmap, CV bullet points.

## Roadmap (not in the 3 days; list it in the README)

HTTPS + custom domain (if not done), Cognito for presenters, NetworkPolicies (minikube `--cni=calico`), Argo CD, Prometheus + Grafana and autoscaling on connection count (KEDA), Redis pub/sub comparison, staging/prod split, WAF.
