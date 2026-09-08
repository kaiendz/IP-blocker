# IP Blacklister

A defensive SOC tool for FortiGate estates: it reads SSL VPN / IKE / admin login-failure logs from your FortiGates (directly, or via FortiCloud), auto-blacklists source IPs that brute-force past a configurable threshold, ingests reputable public threat-intel IP feeds, and publishes the combined blacklist to **Azure Blob Storage** — which each FortiGate's own External Resource (Threat Feed) polls to enforce the block. The app has **no write access to any firewall**; enforcement is entirely publish-and-pull.

## Architecture

```
React (Vite/TS) ── REST ──▶ FastAPI ──▶ PostgreSQL
                                │
                    APScheduler background jobs
                    ├─ poll FortiGate/FortiCloud logs (read-only)
                    ├─ brute-force detection (threshold/window rules)
                    ├─ threat-intel feed refresh
                    ├─ blacklist expiry sweep
                    └─ publish chunked blob(s) to Azure Storage
                                │
                    FortiGate External Resource objects
                    (one per chunk) pull the blob(s) over HTTPS
```

See [`docs/fortigate-setup.md`](docs/fortigate-setup.md) and [`docs/forticloud-setup.md`](docs/forticloud-setup.md) for the device-side configuration this app expects.

## Quickstart (Docker Compose)

```bash
cp .env.example .env
# edit .env — set SECRET_KEY, FERNET_KEY, BOOTSTRAP_ADMIN_PASSWORD, POSTGRES_PASSWORD
docker compose up --build
```

- Frontend: http://localhost:8080
- Backend API docs: http://localhost:8000/docs
- Log in with `BOOTSTRAP_ADMIN_EMAIL` / `BOOTSTRAP_ADMIN_PASSWORD` from your `.env`, then change the password immediately (Users page).

## Local development (without Docker)

**Backend**

```bash
cd backend
python -m venv .venv
./.venv/Scripts/activate   # or `source .venv/bin/activate` on macOS/Linux
pip install -r requirements.txt
cp .env.example ../.env    # or create backend/.env directly — see app/core/config.py for all vars
alembic upgrade head
uvicorn app.main:app --reload
```

**Frontend**

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server proxies `/api` to `http://localhost:8000` (see `frontend/vite.config.ts`).

## Tests

```bash
cd backend
pytest
```

Covers the brute-force threshold/window correlation logic and the Azure blob-chunking logic — both pure functions, tested without a live database or storage account.

## Roles

- **Viewer** — read-only across all pages.
- **Analyst** — everything a Viewer can do, plus: manage blacklist/allowlist entries, poll devices, fetch threat-intel sources, trigger Azure publishes.
- **Admin** — everything, plus: manage devices, FortiCloud/Azure credentials, threat-intel sources, detection rules, users, and view the audit log.

## What's explicitly out of scope (by design)

- Any firewall-write capability — enforcement is publish-to-Azure-and-pull only.
- SSO/LDAP (local accounts only, for now).
- Keyed threat-intel sources (e.g. AbuseIPDB) aren't pre-seeded — the seeded defaults (Spamhaus DROP/EDROP, Blocklist.de, abuse.ch Feodo Tracker) are free, no-key plaintext feeds. Add others via the Threat Intel page.
