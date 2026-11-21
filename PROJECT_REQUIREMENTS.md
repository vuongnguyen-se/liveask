# LiveAsk: Project Requirements

## 1. Purpose

During a class presentation, a club meeting or a small event, the audience rarely asks questions out loud, and the presenter has no quick way to run a poll. **LiveAsk** fixes that:

- The presenter creates a **room** and shows its QR code / 6-character code on the projector.
- The audience opens the link on their phones (no sign-up), **asks questions**, **upvotes** the best ones and **answers polls**.
- Everything updates **in real time** on three views: audience phones, the presenter's control page, and the projector screen.

It is the third project on an AWS-internship CV (SoftwareOne). Its job is to show **Kubernetes on Amazon EKS with a real reason to use containers**, built in **about 3 days**.

### Why containers and not Lambda

Real-time updates need **WebSocket connections that stay open** for the whole talk (30–90 minutes), from tens to hundreds of phones at once. Long-lived connections fit a container that keeps them in memory. API Gateway WebSocket APIs with Lambda are possible, but every message becomes a separate invocation and connection state must live in DynamoDB. The interview story: _"The Say Coffee site is serverless because traffic is light and bursty; LiveAsk is on EKS because it holds long-lived WebSocket connections. I pick the platform by the workload."_

### Portfolio context

| Project | Shows |
|---|---|
| Say Coffee | Serverless web (S3, CloudFront, Lambda, API Gateway, DynamoDB), SAM + Terraform, GitHub OIDC |
| CloudDocs-AI | AI on AWS: Bedrock Knowledge Bases (RAG), Cognito, CDK |
| **LiveAsk** | Containers and Kubernetes on EKS: WebSockets, multi-pod fan-out, autoscaling, zero-downtime updates, VPC networking |

## 2. Users

| Role | How they get in | Can do |
|---|---|---|
| **Presenter (host)** | Creates a room; gets a secret host link | Open/close polls, mark questions answered, hide questions, close the room |
| **Audience** | Room link or 6-character code; optional display name | Ask questions, upvote (once each), vote in polls (once each) |
| **Screen** | Screen link (read-only) on the projector | Shows top questions and live poll results |

No accounts in the MVP. Rooms expire after 24 hours.

## 3. Functional requirements

- **FR-1 Rooms:** create a room with a title. You get a 6-character code (no ambiguous characters such as 0/O, 1/I), an audience URL, a screen URL and a host URL. The host URL carries a secret token. Rooms expire 24 h after creation; a nightly job deletes expired rooms and their data.
- **FR-2 Questions:** audience posts a question (1–280 chars, optional name ≤ 40 chars). It appears for everyone within 1 s. The list is sorted by votes, then newest first.
- **FR-3 Upvotes:** one upvote per question per audience device (anonymous device ID stored in the browser). Tapping again removes the vote.
- **FR-4 Moderation:** host can mark a question `answered` or `hidden`. Hidden questions disappear for audience and screen.
- **FR-5 Polls:** host creates a poll (question + 2–6 options), opens it, closes it. One vote per device. Live result bars on all views.
- **FR-6 Real time:** every change (new question, vote count, status, poll) is pushed over WebSocket to all clients in the room, **no matter which pod they are connected to**.
- **FR-7 Reconnect:** if the connection drops (pod restart, network), the client reconnects automatically with backoff and reloads the room state.
- **FR-8 Limits:** max 5 questions per device per minute; max 300 connections per room (configurable).

## 4. Non-functional requirements

| ID | Requirement |
|---|---|
| NFR-1 | Real-time delivery < 1 s across pods for 200 connected clients |
| NFR-2 | **Zero-downtime deploys:** during a rolling update, no data is lost and clients reconnect within ~5 s |
| NFR-3 | Runs with ≥ 2 replicas; survives losing one pod or one node (PDB, spread across AZs) |
| NFR-4 | Autoscales on load (HPA), demonstrated with a load test |
| NFR-5 | Same Kubernetes manifests run on **minikube** (free) and **EKS** (Kustomize overlays) |
| NFR-6 | All AWS infrastructure in Terraform; no long-lived AWS keys (GitHub OIDC) |
| NFR-7 | One AWS session ≈ 3–4 hours ≈ USD 1, then everything is destroyed |
| NFR-8 | No personal data collected beyond an optional display name |

## 5. Out of scope (roadmap ideas for the README)

HTTPS on a custom domain (if time allows on day 3), Cognito sign-in for presenters, NetworkPolicies (needs Calico on minikube), Argo CD (GitOps), Prometheus/Grafana and autoscaling on connection count (KEDA), Redis pub/sub instead of Postgres `LISTEN/NOTIFY`, React frontend, separate prod environment, WAF.
