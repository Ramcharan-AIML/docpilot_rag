# Teach: the front door - DNS, HTTPS, reverse proxy, Caddy (B3 and C6, from zero)

Simple English. Written 2026-10-23, before B3 is built. Real results added after.

---

## 1. The big picture: how a visitor reaches DocPilot

```text
Visitor types  https://docpilot-xyz.duckdns.org
   |
   | 1. DNS: "which computer is docpilot-xyz.duckdns.org?"  ->  13.234.x.x (my server)
   v
Server 13.234.x.x, port 443 (HTTPS)
   |
   | 2. Caddy: the front door. Unlocks HTTPS, then passes the request inside
   v
app container, port 8000 (FastAPI + React)  ---->  qdrant container, port 6333
   (not reachable from the internet)               (not reachable from the internet)
```

**Real-life example: an apartment building.** DNS is the address book ("Ram lives at
house 13"). Caddy is the security guard at the gate: checks and opens the sealed envelopes
(HTTPS), then walks the visitor to the right flat (the app). The flats themselves have no
door to the street.

---

## 2. DNS (the internet's address book)

| Word | Meaning |
|---|---|
| **IP address** | the real number of a computer, like `13.234.56.78` (hard to remember) |
| **Domain name** | a name for it, like `docpilot-xyz.duckdns.org` |
| **DNS** | the system that turns a name into an IP address |
| **A record** | one line in DNS: "this name -> this IPv4 address" |
| **DuckDNS** (our choice, C6) | a free service that gives a name `<something>.duckdns.org` and lets me set its A record |

**Why a name and not just the IP?** HTTPS certificates are given to NAMES. Free
certificates (Let's Encrypt) are not given for a bare IP in the normal way, and a name
looks professional on a CV.

**Why DuckDNS?** Free forever, no card. **Why not a paid .com?** Costs money (my rule: 0).
**Why not AWS Route 53?** About $0.50 a month per zone: not free.

---

## 3. HTTPS (the sealed envelope)

- **HTTP** = sending a postcard: anyone on the way (Wi-Fi owner, internet provider) can
  read it, including chats and uploaded files.
- **HTTPS** = HTTP inside a locked envelope (**TLS** encryption). Only the browser and the
  server can open it.
- **Certificate** = the server's ID card, signed by a trusted authority, saying "this
  public key really belongs to docpilot-xyz.duckdns.org". The browser checks it; the
  padlock appears.
- **Let's Encrypt** = a free, automatic certificate authority. Certificates last 90 days
  and must be renewed.
- **Port 80** = plain HTTP, **port 443** = HTTPS. Let's Encrypt proves I own the name by
  calling my server on port 80 (the "HTTP challenge"), so port 80 must be open too.

---

## 4. Reverse proxy (the security guard)

A **reverse proxy** sits in front of the app and forwards requests to it.

| Job | Why we need it |
|---|---|
| HTTPS: get + renew certificates, decrypt | uvicorn could do TLS, but getting and renewing certificates by hand is error-prone |
| One public door (80/443) | the app (8000) and Qdrant (6333) stay private inside Docker's network |
| Passes the visitor's real IP (`X-Forwarded-For`) | our A2 rate limits need the real IP, not the guard's |
| Streams replies through | Caddy flushes `text/event-stream` (our live answers) at once (checked in Caddy docs 2026-10-23) |

**Why Caddy?** It gets and renews Let's Encrypt certificates **automatically** with a
2-line config file. **Why not Nginx?** Very popular (good interview word) but HTTPS needs
extra tools (certbot) and more config. **Why not Traefik?** Powerful with labels, more to
learn. **Why not AWS load balancer + ACM?** About $16+ a month: not free (Rule 17: no LB).

Our whole Caddyfile:
```text
{$DOMAIN} {
    encode gzip
    reverse_proxy app:8000
}
```
`{$DOMAIN}` comes from an environment variable: `localhost` on my laptop, the DuckDNS name
on the server. For `localhost`, Caddy makes its OWN local certificate (the browser shows a
warning because my Windows does not trust Caddy's private authority; that is expected).

---

## 5. Docker Compose for production (the whole building in one file)

`docker-compose.prod.yml` starts 3 containers together:

| Service | Image | Public? | Notes |
|---|---|---|---|
| `caddy` | `caddy:2.11.7-alpine` | YES: ports 80 + 443 | certificates saved in a volume (so restarts don't ask Let's Encrypt again: they have rate limits) |
| `app` | my DocPilot image | no | `PUBLIC_MODE=1`; `QDRANT_URL=http://qdrant:6333`; chats + uploads in a volume |
| `qdrant` | `qdrant/qdrant:v1.19.1` | no | index in a volume |

| Word | Meaning |
|---|---|
| **Service name as address** | inside Compose, containers find each other by NAME: `http://qdrant:6333`, `app:8000` (Docker's own DNS) |
| **`restart: unless-stopped`** | if the app crashes or the server reboots, Docker starts it again |
| **`mem_limit`** | the most RAM a container may use; above it, only THAT container is killed, not the whole server |
| **Named volume** | a storage folder managed by Docker; survives `down` and image upgrades (never `down -v`!) |
| **`FORWARDED_ALLOW_IPS=*`** | tells uvicorn to trust `X-Forwarded-For`. Safe ONLY because port 8000 is not public: the only caller is Caddy |

---

## 6. Interview questions

**Q1. What happens when I type a URL?** DNS turns the name into an IP; the browser opens a
TCP connection to port 443; TLS handshake (certificate checked, keys agreed); then the
encrypted HTTP request goes to the reverse proxy, which forwards it to the app.

**Q2. Why a reverse proxy in front of the app?** One public door: TLS termination and
automatic certificates, the app and database stay private, real client IP forwarded,
compression, and later load balancing across several app copies.

**Q3. How does Let's Encrypt know you own the domain?** The ACME HTTP-01 challenge: it
asks for a token at `http://<domain>/.well-known/acme-challenge/...` on port 80; only the
server the domain points to can answer.

**Q4. Why must uvicorn only trust X-Forwarded-For from the proxy?** Anyone can write that
header. If the app trusted it from the internet, an attacker could fake a new IP on every
request and skip IP rate limits.

**Q5. How do containers in Compose talk to each other?** Over a private Compose network,
by service name (Docker's built-in DNS). Only ports listed under `ports:` are reachable
from outside.

---

## 7. Real results (filled after each step)

| Step | Result | Date |
|---|---|---|
| B3 on the laptop | n/a (not run yet) | |
