Continues from [3_phase_7_production.md](3_phase_7_production.md)

# Phase 7: Production (Implementation Plan, Part 4 of 4): finish, move, prove

Part 4 covers 7.16 to 7.19 and the final gate.

---

## Step 7.16: Load testing

**File:** `loadtest/locustfile.py` (Locust, VERIFY version; k6 is the alternative).

Scenarios:
1. Steady users asking cached questions (cache path).
2. Steady users asking new questions (full path). Free-tier LLM limits: few users, or point
   the gateway at Ollama or a mock LLM for this run.
3. A burst above the rate limit: expect `429`s, not errors.
4. Provider failure: bad key for the first provider: expect fallbacks, no `5xx`.
5. On k3s: run scenario 2 while doing a rolling deploy: count failed requests (should be 0).

Report p50/p95 latency, error rate, 429 rate, fallback count, CPU/RAM on the instance
(CloudWatch + Grafana), with the instance type named. Latency without hardware context means
nothing. Watch the AWS budget during the run.

---

## Step 7.17: Incremental ingestion

**File:** `src/docpilot/ingestion/manifest.py`; manifest table in Postgres.

```text
for each document in the raw-docs bucket (S3 on AWS, SeaweedFS locally):
    new_hash = sha256(cleaned text)
    if new_hash == manifest[source]:  skip
    else: delete this source's points (filter by source), re-chunk, re-embed, upsert,
          manifest[source] = new_hash, version += 1
for each source in the manifest but no longer in the bucket: delete its points
then: bump cache versions; take a fresh Qdrant snapshot to the snapshots bucket
```

Runs as a Kubernetes **CronJob** (`deploy/k8s/ingest-cronjob.yaml`) or by hand.
**Test:** change one doc, run: only that doc's chunks change (count the upserts).

---

## Step 7.18: The Oracle move (decision D-018)

The AWS free plan ends at 6 months (suspension, then deletion). The public demo moves to
Oracle Cloud Always Free, permanently free.

**Now (during Phase 7): prepare and rehearse**
1. VERIFY Oracle Always Free: current ARM (A1) allowance, region capacity, sign-up rules.
2. `infra/modules/oracle_app_host/` (VCN, subnet, security list 80/443, A1 VM, object storage
   bucket) and `infra/envs/oracle/`. Same outputs as the AWS module; same `cloud-init.sh`.
3. `terraform plan` for Oracle and read it. Create the account and apply only when ready to
   move (or earlier for a rehearsal if the always-free allowance permits; record cost = 0).
4. Images: arm64 builds already go to GHCR (7.10). The Oracle VM pulls from GHCR.
5. Secrets on Oracle: its vault service or an env file written by the boot script
   (VERIFY options; decision entry).

**At month 5: the move (checklist, record each tick in `progress.md`)**
- [ ] Qdrant snapshot -> download -> upload to the Oracle bucket (or SeaweedFS on the VM)
- [ ] `terraform apply` in `envs/oracle`
- [ ] k3s up via cloud-init; apply `deploy/k8s/`; restore the snapshot into the PVC
- [ ] point DuckDNS at the Oracle IP; certificate issued
- [ ] `/ready` green; eval smoke test on the live system; dashboards show traffic
- [ ] switch `deploy.yml` to the Oracle target (deploy over a method chosen in the decision
      log, e.g. a pull-based script on the VM, since SSM is AWS-only)
- [ ] `terraform destroy` in `envs/aws`; ECR and S3 emptied first; Billing shows nothing running
- [ ] README updated: "migrated AWS -> Oracle in N hours" (a real number, if you measured it)

---

## Step 7.19: README, demo, and the big interview file

1. `README.md`: one-paragraph pitch; architecture diagram; **the ablation table with real
   numbers** (generated from MLflow); the safety table; screenshots of the failing CI gate,
   the Grafana RAG dashboard, an MLflow comparison view; demo link; run-it-yourself steps;
   the AWS -> Oracle portability story; an honest limitations section.
2. Demo UI: a small Gradio or Streamlit page (`ui/app.py`) calling the public API with a demo
   key, hosted on a Hugging Face Space (VERIFY free CPU limits and sleep behaviour). Strict
   rate limit on the demo key.
3. Short demo video or GIF (free screen recorder).
4. Merge all `docs/interview/phase_*_interview.md` (and their `2_` parts) into
   `docs/interview/ALL_INTERVIEW_QUESTIONS.md` (+ `2_`, `3_` parts by Rule 1), with real
   numbers wherever a `n/a` placeholder was.

---

## Security checklist (from `PROJECT_DOCUMENTATION.md` 15.8, extended for AWS)

- [ ] no secrets in git, images, or Terraform state in plain text; secrets in SSM Parameter Store
- [ ] root user unused with MFA; daily identity with MFA
- [ ] no long-lived AWS keys anywhere (OIDC for CI, instance role for the server)
- [ ] security group: 80/443 only; no SSH port; SSM sessions only
- [ ] S3 public access blocked; state bucket versioned
- [ ] non-root containers; only the ingress / Caddy is public; Grafana behind a password
- [ ] CORS limited to the UI origin; input size limits; rate limiting; PII-free logs
- [ ] pip-audit in CI; Dependabot / secret scanning on
- [ ] budget alerts on; everything tagged `project=docpilot`

---

## Phase 7 gate (and the project's definition of done)

- [ ] public HTTPS URL on AWS (k3s on EC2), auth and rate limit on
- [ ] all infrastructure created by Terraform; `plan` shows no changes; nothing clicked by hand
- [ ] CI: test, eval-gate, audit, terraform-check required on `main`; gate failure proven
- [ ] CD: merge to `main` builds amd64+arm64, pushes ECR+GHCR, deploys via SSM, smoke-tests
- [ ] traces and Grafana (app + RAG monitoring) show real traffic; one alert fired on purpose;
      CloudWatch alarms in place; D-009 closed
- [ ] semantic cache false-hit rate measured (or cache disabled with reason)
- [ ] load test report with real numbers and the instance type
- [ ] HITL works with the Postgres checkpointer across a pod restart
- [ ] EKS exercise done (plan read; if applied, destroyed and cost recorded)
- [ ] Oracle env planned and rehearsed; move date in the calendar
- [ ] README complete; big interview file assembled
- [ ] every version pinned and verified; merged via PR; tag `phase-7` pushed
- [ ] everything in `PROJECT_DOCUMENTATION.md` section 23 checked
