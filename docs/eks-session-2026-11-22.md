# EKS sessions, 2026-11-22

Two billable sessions on Amazon EKS (`ap-southeast-1`, account `clouddocs-dev`), each destroyed afterwards. Session 1 (about 50 minutes) proved the design and found the infrastructure problems. Session 2 (about 1 hour 35 minutes from the apply to the end of the destroy) ran the fixed Terraform from a clean start, the deploy script, the real-phone test and the checks again. Sections below: session 1, its problems, session 2, then the teardown.

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

## Session 2: the fixed Terraform, the deploy script, a real phone

Started about 12:50; the destroy began at 14:13 and finished at 14:24. Kubernetes 1.35, 2 Spot nodes in `ap-southeast-1a` and `ap-southeast-1b`, RDS, the same ALB settings.

| Check | Result |
|---|---|
| `terraform apply` from a clean state | 78 resources added in one run, no errors: the Local Zone and OIDC fixes held |
| Deploy to EKS workflow | built and pushed the image; its last step now prints the command to run next |
| `scripts/deploy-from-laptop.sh` | first full run worked: it checked the image, applied the manifests, waited for the rollout and printed the ALB address |
| `e2e/run.js` through the ALB | 19 of 19 (after the room-creation limit was added) |
| `e2e/rollout.js` | 6 of 6: 13 of 13 questions stored, 0 failed requests, never below 2 replicas, a 20 s rollout, the screen reconnected to a new pod and caught up |
| `scripts/load_test.py`, 200 clients, 60 s, 6 burn workers | 200 of 200 connected (100 on each of 2 pods); 22,400 of 22,400 deliveries; median 261 ms, **p95 801 ms**, max 2,959 ms; POST median 164 ms |
| HPA | 2 to 6 pods at CPU 716% of the 60% target |
| ALB target group | all 6 targets healthy; health check `/readyz`, target type `ip` |
| **Phone test** | **passed**: run by the presenter on phones over mobile data, against the ALB address (plain HTTP) |

Across the two sessions the load test's p95 was 733 ms and 801 ms, both under the 1 s target. The worst single delivery was 1,079 ms in session 1 and 2,959 ms in session 2, so the tail is worth watching on a longer run. Each run was 60 seconds.

### Findings from the phone test

1. The presenter's page showed two long links but not the room code, so on a phone there was nothing to type on another device. The page now shows the code large with a Copy code button.
2. The join field was only in the footer, about eleven screens down on a phone. The hero now has a "Have a room code? Join a room" link that jumps to it.
3. In a short desktop window (for example 1325 by 660) the footer links were drawn over the create form, because the kit fixes the closing block at one screen from 1280 px up. The block now grows past the screen, as the kit already does from 640 to 1279 px.

The landing page is still about 11.5 phone screens tall; if that feels too long, it needs a design decision, not a bug fix. A screenshot of the console and of the phone were not saved; the evidence for pods across zones, the autoscaler and the target group is the terminal output above.

## Teardown

Run in this order: `kubectl delete -k k8s/overlays/aws` (so the ALB is gone), then `terraform destroy`.

Both sessions were checked afterwards with the same searches (region `ap-southeast-1`): no EKS cluster, EC2 instance, NAT gateway, Elastic IP, load balancer, RDS instance, EBS volume or non-default VPC; no LiveAsk IAM role, ECR repository, budget, secret, KMS alias or log group. `terraform destroy` removed 78 resources each time. The resource-tag search still listed five stale entries after each destroy (a security group and its rule, a NAT gateway, KMS keys); looking each up showed the security group and rule are gone, the NAT gateway is `deleted` and the KMS keys are `PendingDeletion`, which costs nothing. The account's GitHub OIDC provider is shared and was not touched. Still to do: confirm in Cost Explorer on 2026-11-23.
