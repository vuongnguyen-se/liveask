# EKS session, 2026-11-22

One billable session on Amazon EKS (`ap-southeast-1`, account `clouddocs-dev`), about 40 minutes of running time. Everything was destroyed afterwards (see the teardown note at the end).

## What ran

- Kubernetes 1.35 (standard support until 2027-03-27), 2 Spot nodes in `ap-southeast-1a` and `ap-southeast-1b`, RDS PostgreSQL (single AZ), the AWS Load Balancer Controller, metrics-server.
- The image was built and pushed to ECR by the **Deploy to EKS** workflow; the manifests were applied from the laptop (see "Problems").
- ALB: idle timeout 3600 s, deregistration delay 30 s, health check `/readyz`.

## Results

| Check | Result |
|---|---|
| `e2e/run.js` through the ALB | 19 of 19 passed; host and screen were on different pods |
| `e2e/rollout.js` (`kubectl rollout restart`) | 6 of 6 passed; 12 of 12 questions stored, 0 retried requests, replicas never below 2, the screen reconnected to a new pod and caught up; the rollout took 10 s |
| `scripts/load_test.py`, 200 WebSocket clients, 60 s, 6 burn workers | 200 of 200 connected (101 and 99 on two pods); 22,600 of 22,600 deliveries; latency median 235 ms, **p95 733 ms**, max 1,079 ms; POST median 150 ms. NFR-1 (p95 under 1 s) passed in this run |
| HPA | 2 to 6 pods (its maximum) at CPU 624% of the 60% target |
| ALB target group | all 6 pod targets healthy |
| Pod placement | 2 nodes in 2 zones; 3 pods on each node |

The load test is one 60-second run, so it is one measurement, not a guarantee. Locally the same test gave p95 1,079 ms, mostly the Windows tunnel.

Not done: the check from a real phone on mobile data, and screenshots of the AWS console.

## Problems found and fixed

1. **NAT gateway failed.** `ap-southeast-1` lists the Hanoi Local Zone first, and a Local Zone has no NAT gateway. The availability-zone lookup now keeps standard zones only (`providers.tf`). Replacing the subnets also needed the two old private subnets deleted first, because the new ones reused their address ranges.
2. **GitHub could not assume the deploy role.** This repository uses immutable OIDC subjects (`repo:owner@ID/name@ID:...`). The new variable `github_oidc_repo_claim` carries that value; it defaults to `github_repo`. The first run after the policy change also failed once while IAM propagated.
3. **The deploy workflow cannot reach an IP-locked cluster.** The workflow builds and pushes the image, but its `kubectl apply` times out because GitHub-hosted runners are not on the allowed IP list. The manifests were applied from the laptop instead. Opening the API to `0.0.0.0/0` was not done on purpose.
4. Microsoft Edge on the laptop refused the ALB address with `ERR_BLOCKED_BY_CLIENT`; Chrome worked.

## Teardown

Run in this order: `kubectl delete -k k8s/overlays/aws` (so the ALB is gone), then `terraform destroy`. The outcome is recorded in `CURRENT_STATE.md`.
