# Teach: CI/CD and the container registry (B5, from zero)

Simple English. Written 2026-10-24, before the workflow runs. Real results added after.

---

## 1. CI vs CD

| Word | Meaning | DocPilot |
|---|---|---|
| **CI** (Continuous Integration) | every change is tested automatically before it joins `main` | `ci.yml`: tests, lint, eval gate on every PR (since Phase 1) |
| **CD** (Continuous Delivery) | every change that passed CI is packaged automatically, ready to deploy | `image.yml` (new): builds the Docker image and stores it in GHCR |
| **Continuous Deployment** | ...and also installed on the server automatically | later (Stage D): today I deploy by hand with one command |

**Real-life example: a bakery.** CI = the quality check on every batch of dough. CD = the
bread that passed is packed and put on the delivery shelf. Deployment = the van takes it
to the shop. Today the van is me.

**Why build in GitHub, not on my laptop?**
- The same clean machine every time: no "it built on my laptop because of some old file".
- Every image is linked to an exact git commit: I always know which code is live.
- The server downloads a finished image; it never needs my laptop.

---

## 2. GHCR (GitHub Container Registry)

A **registry** is a shared fridge for images: CI puts the box in, the server takes it out.

| Choice | Why | Why not |
|---|---|---|
| **GHCR** `ghcr.io/ramcharan-aiml/docpilot` | free for public images; lives next to my code; login with the built-in `GITHUB_TOKEN` (no secret to create) | **Docker Hub**: free tier has pull rate limits and needs a separate account + token. **AWS ECR**: costs per GB stored after the free allowance, and needs AWS keys in GitHub |

**Image names must be lowercase** (a Docker rule), so `Ramcharan-AIML` becomes
`ramcharan-aiml`.

---

## 3. Tags: which version is this?

Every image gets 2 tags:

| Tag | Example | Used for |
|---|---|---|
| `sha-<commit>` | `sha-3f9c2ab` | **the exact code**. The server runs THIS (pinned, repeatable, easy rollback) |
| `latest` | `latest` | a moving label: "newest build of main". Handy for trying, never for pinning |

**Rollback** = change the tag on the server back to the previous `sha-...` and restart.
That is why we never deploy `latest` in production.

---

## 4. How the workflow runs

```text
I merge a PR into main
  -> ci.yml runs (tests + eval gate)                 [already exists]
  -> only if CI is GREEN: image.yml starts           [new, "workflow_run"]
       1. checkout the exact commit CI tested
       2. Buildx (Docker's builder) + the GitHub cache of layers
       3. log in to ghcr.io with GITHUB_TOKEN
       4. build the Dockerfile for linux/amd64 (the t3.small is Intel/AMD)
       5. push  ghcr.io/ramcharan-aiml/docpilot:sha-xxxxxxx  and  :latest
```

| Word | Meaning |
|---|---|
| **workflow_run** | "start this workflow when another one finishes". We start only if CI succeeded: no image from broken code |
| **workflow_dispatch** | a "Run workflow" button in the Actions tab, for a manual build |
| **`GITHUB_TOKEN`** | a password GitHub creates for each run and deletes after it. `permissions: packages: write` lets it push images, nothing more |
| **Least privilege** | give a job only the rights it needs: here `contents: read` + `packages: write` |
| **Layer cache (`type=gha`)** | Docker layers saved in GitHub's cache: if only my code changed, torch (873 MB) is not reinstalled |
| **Pinned action versions** | `docker/login-action@v4.6.0`, not `@main` or `@latest`: someone else's change cannot silently change my pipeline |

**Why only amd64 now?** The AWS t3.small is Intel/AMD. ARM (for Oracle later) would be
built through an emulator (QEMU) on GitHub's machines: installing torch emulated is very
slow. Added when the Oracle move happens.

---

## 5. Making the image downloadable by the server

A new GHCR package is usually **private**. The server then needs a password to pull it.
Simplest safe option for us: make the package **public** once (Package settings ->
Change visibility). It contains only code that is already on public GitHub, the models
(open licences) and no secrets (`.dockerignore` keeps `.env` out; checked in B1).

---

## 6. Interview questions

**Q1. CI vs CD?** CI tests every change before merging; CD packages every tested change
into a deployable artifact (our Docker image in GHCR); continuous deployment also rolls it
out automatically.

**Q2. Why tag images with the commit SHA?** It makes a deploy reproducible and traceable
(which code is live), and rollback is just switching back to the previous SHA tag.
`latest` changes underneath you.

**Q3. How does your pipeline avoid shipping broken code?** The image workflow is triggered
by `workflow_run` only when the CI workflow (tests + eval gate) succeeded on main, and it
checks out that exact commit.

**Q4. How do you keep the pipeline secure?** No long-lived secrets: the short-lived
`GITHUB_TOKEN` with least-privilege permissions; actions pinned to exact versions; no
secrets baked into the image.

**Q5. Why cache layers in CI?** Building torch and the packages takes minutes; with the
GitHub Actions cache only changed layers rebuild, so small code changes build fast.

---

## 7. Real results (filled after the first run)

| Check | Result | Date |
|---|---|---|
| First image build in Actions | n/a (not run yet) | |
| Second build (cache) | n/a | |
| Image in GHCR + visibility | n/a | |
