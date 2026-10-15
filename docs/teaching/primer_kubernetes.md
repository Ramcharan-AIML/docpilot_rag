# Primer: Kubernetes, k3s, and EKS

Used in: Phase 7 (k3s is **planned**, not optional; EKS is a short exercise only).
Decisions: D-021 (k3s), D-023 (EKS exercise).

---

## 1. Like I'm five

- **Docker Compose** is a to-do list taped to the wall of **one kitchen**: "start the oven,
  start the fridge, start the coffee machine". If the oven breaks, someone must notice and
  restart it.
- **Kubernetes** is a **restaurant manager**. You tell the manager what you want ("always
  have 2 cooks making pasta, 1 dishwasher"), and the manager keeps it that way: replaces a
  sick cook, adds cooks at lunch rush, swaps cooks one by one when a new recipe arrives, and
  only sends customers to cooks who are ready.

You describe the **desired state**; Kubernetes keeps reality matching it, all the time.
(Terraform does this for infrastructure; Kubernetes does it for running containers.)

---

## 2. The words (with our examples)

| Kubernetes word | Child meaning | DocPilot example |
|---|---|---|
| **Cluster** | the whole restaurant | one k3s cluster on the EC2 server |
| **Node** | one kitchen (a machine) | the EC2 instance (one node) |
| **Control plane** | the manager's office | k3s server process |
| **Pod** | one cook's workstation: one or more containers that live and die together | one `api` container |
| **Deployment** | "always keep N of these pods running, update them gradually" | `api` Deployment, 1 replica |
| **StatefulSet** | like a Deployment, but each pod keeps its own storage and name | Qdrant, Postgres |
| **Service** | a fixed name and address for a group of pods | `qdrant` -> whichever pod is Qdrant right now |
| **Ingress** | the front door: routes web traffic by host/path to Services | `docpilot.<domain>` -> `api` Service |
| **ConfigMap** | a settings sheet | `TOP_K`, model names |
| **Secret** | a locked settings sheet | Groq key, Postgres password |
| **PersistentVolumeClaim (PVC)** | "I need 10 GB of disk that survives restarts" | Qdrant data, Postgres data |
| **Namespace** | a separate section of the restaurant | `docpilot` |
| **Liveness probe** | "is this cook still alive?" -> restart if not | `GET /health` |
| **Readiness probe** | "is this cook ready to take orders?" -> no traffic until yes | `GET /ready` |
| **Requests / limits** | minimum guaranteed CPU/RAM, and maximum allowed | api: request 1.5 GiB, limit 3 GiB (tune from measurements) |
| **kubectl** | the walkie-talkie to the manager | `kubectl get pods -n docpilot` |
| **Manifest** | a YAML file describing the desired state | `deploy/k8s/api-deployment.yaml` |

---

## 3. From Compose to Kubernetes: the translation table

| `docker-compose.yml` | Kubernetes |
|---|---|
| `services: api:` | Deployment + Service |
| `services: qdrant:` with a volume | StatefulSet + Service + PVC |
| `ports: "8000:8000"` | Service (inside), Ingress (outside) |
| `environment:` | ConfigMap (plain) + Secret (sensitive) |
| `healthcheck:` | liveness and readiness probes |
| `restart: unless-stopped` | built in: the Deployment always restores pods |
| `depends_on:` | no direct equivalent: apps must retry until dependencies are ready (readiness probes help) |
| Caddy for HTTPS | Ingress controller (k3s ships Traefik, VERIFY) + certificates (Traefik's ACME or cert-manager, VERIFY) |

Same images, same app. Only the "how to run it" files change.

---

## 4. A manifest, explained line by line

```yaml
# deploy/k8s/api-deployment.yaml (sketch; VERIFY API versions)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
  namespace: docpilot
spec:
  replicas: 1                          # one copy is enough on one small node
  selector:
    matchLabels: {app: api}
  template:                            # the pod "recipe"
    metadata:
      labels: {app: api}
    spec:
      containers:
        - name: api
          image: <ecr-repo>/docpilot-api:<git-sha>   # never ":latest"
          ports: [{containerPort: 8000}]
          envFrom:
            - configMapRef: {name: docpilot-config}
            - secretRef: {name: docpilot-secrets}
          readinessProbe:              # no traffic until Qdrant/Redis/Postgres are reachable
            httpGet: {path: /ready, port: 8000}
          livenessProbe:               # restart the pod if the process hangs
            httpGet: {path: /health, port: 8000}
          resources:
            requests: {memory: "1536Mi", cpu: "500m"}   # tune from real measurements
            limits:   {memory: "3Gi"}
```

**Rolling update:** change the image tag, `kubectl apply`, and Kubernetes starts the new pod,
waits until it is **ready**, then stops the old one. With one replica and limited RAM, this
needs room for two api pods briefly; we check that.

---

## 5. Why k3s (and not "full" Kubernetes) on our server

k3s is a lightweight, certified Kubernetes distribution in one small binary. It includes
what a single node needs (an ingress controller and simple local storage, VERIFY current
defaults). The k3s docs (checked 2026-10-08) list **2 GB RAM minimum for a server node**,
and their own profiling shows about 1.6 GB used with a small workload. That fits on the
`m7i-flex.large` alongside our stack only after we measure real usage; if not, we trim
(e.g. smaller Grafana/Prometheus retention).

| Option | Why not |
|---|---|
| kubeadm "full" Kubernetes | more components and RAM than one small VM should spend |
| minikube / kind | built for laptops and CI testing, not for a real server |
| EKS for production | the control plane alone costs USD 0.10/hour (checked 2026-10-08), even idle: it would eat the credits |

**Order in Phase 7:** Compose first (simplest, proves the containers work), then k3s on the
same VM with the same images. The live public deployment runs on k3s; Compose stays for
local development.

---

## 6. EKS: the managed Kubernetes exercise

**Like I'm five:** EKS is renting a restaurant manager from Amazon. Amazon runs the manager's
office for you (upgrades, backups, high availability). You pay for the manager by the hour
even when the restaurant is empty.

**Facts (checked 2026-10-08):** EKS charges USD 0.10 per cluster per hour for the control
plane, plus the worker nodes and networking. There is no free control plane.

**The exercise (decision D-023):**
1. Default: `infra/eks_exercise/` with the official community EKS module (VERIFY), and run
   **`terraform plan` only**. Read the plan: VPC, subnets, node group, IAM roles. That alone
   teaches what EKS needs.
2. Optional, only if credits allow and you set a timer: `apply` -> `kubectl apply` the same
   manifests -> see the app run -> **`terraform destroy` in the same sitting** -> check
   Billing and EC2 Global View that nothing is left. Record the real cost from Billing.
3. **Never leave it running.** Not overnight, not "for later".

Interview answer: "For one node I ran k3s; I know EKS and exercised it with Terraform, but a
managed control plane costs money per hour, so it only makes sense when the scale or the
team needs it."

---

## 7. Commands you will use

```powershell
kubectl get nodes                       # is the cluster up?
kubectl get pods -n docpilot            # what is running?
kubectl describe pod <name> -n docpilot # why is it not starting? (read Events at the bottom)
kubectl logs deploy/api -n docpilot     # app logs
kubectl apply -f deploy/k8s/            # make the cluster match the files
kubectl rollout status deploy/api -n docpilot
kubectl rollout undo deploy/api -n docpilot   # roll back to the previous version
```

---

## 8. Self-check

1. Compose vs Kubernetes with the kitchen/manager story.
2. Pod, Deployment, StatefulSet, Service, Ingress: one line each.
3. Liveness vs readiness probe: what does each do on failure?
4. Translate our Compose file to Kubernetes objects.
5. Why k3s for production here, and not EKS?
6. Describe the EKS exercise and its safety rule.
