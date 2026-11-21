# Initial Prompt for the Coding Agent (Orca)

Copy everything below the line into Orca as the first message of a new session.

---

You are helping me build **LiveAsk**, a portfolio project: a real-time Q&A and polling web app for presentations, running on **Amazon EKS**. The audience scans a QR code, asks and upvotes questions and answers polls; the presenter's page and the projector screen update live over WebSockets. It is the third project on my CV for an **AWS internship at SoftwareOne**. Its purpose is to show practical **Kubernetes** knowledge with a real reason to use containers, and it must be finished in **about 3 days**.

The repository already contains a working, validated EKS platform (Terraform, Kubernetes manifests, CI/CD) running a placeholder "notes" API. We replace the app and adapt the manifests; we do not rebuild the platform.

First, read every Markdown file in the project root and treat them as the source of truth, in this order:

1. `CURRENT_STATE.md`: what exists, what was verified, machine and account notes
2. `AI_CODING_RULES.md`: how to work in this repo
3. `PROJECT_REQUIREMENTS.md`: purpose, users, features, out of scope
4. `ARCHITECTURE.md`: design, the multi-pod real-time problem, Kubernetes objects, target layout
5. `DATABASE_DESIGN.md`, `API_SPECIFICATION.md`
6. `SECURITY_AND_COST.md`
7. `DECISIONS.md`: decisions already made; do not reopen them without a reason
8. `TASKS.md`: the 3-day task board; the next task is the first unticked one

## Your first assignment

Do not write code yet.

1. Inspect the repository and confirm it matches `CURRENT_STATE.md`.
2. List anything in the docs that is contradictory or unclear.
3. Propose how you will do **Day 1** (tasks D1-01 to D1-07): order, files per task, and the libraries you will add to `requirements.txt` (keep the list short).
4. Do not create AWS resources or deploy anything.
5. Wait for my approval, then do one task at a time.

## Teaching expectations

I am learning Kubernetes and AWS. Explain decisions briefly and practically. For each task:
- State the task ID and objective.
- List the files you will create or change.
- Implement the smallest change that passes the task's **Done when** check, with tests.
- Tell me exactly how to run and verify it on Windows (PowerShell or Git Bash).
- Update `TASKS.md` and `CURRENT_STATE.md`.
- Give me 2–3 interview questions about what we just built.

Never claim code, tests, deployments or AWS resources worked unless you verified them. Ask before any step marked 💰.
