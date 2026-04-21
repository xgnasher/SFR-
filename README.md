# SVCTE Staff Finance Registrar

An internal web app for staff to **log, approve, and track software purchase requests** before they're placed with vendors. Built as a school project.

---

## What it does

- Staff log in and submit requests for software they want the school to buy (software name, vendor, cost, number of seats, business justification)
- Requests move through a status pipeline: **Pending → In Review → Approved / Rejected**
- Approvers review pending requests and make a decision
- Each user sees their dashboard with total approved spend and a count of pending items
- Three roles supported: **Requester**, **Approver**, **Admin**

---

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Python + FastAPI |
| Database | SQLite (via SQLAlchemy ORM) |
| Templates | Jinja2 (server-rendered HTML) |
| Auth | Cookie-based session with SHA-256 password hashing |
| Dev environment | Docker + Docker Compose |
| IDE integration | VS Code Dev Containers |

---

## Project structure

```
softreq-container/
├── app/
│   ├── __init__.py
│   └── main.py              ← FastAPI app, routes, DB models (teammate's code)
├── templates/               ← Jinja2 HTML templates
│   ├── landing.html         (login page)
│   ├── dashboard.html       (list of user's requests)
│   └── new_request.html     (submit form)
├── static/                  ← CSS, JS, images referenced by templates
├── data/                    ← SQLite DB lives here (gitignored, persists across restarts)
├── .devcontainer/
│   └── devcontainer.json    ← VS Code "Reopen in Container" config
├── Dockerfile               ← builds the Python 3.12 image
├── docker-compose.yml       ← runs the container on port 8000
├── requirements.txt         ← Python dependencies
├── .dockerignore
├── .env.example             ← copy to .env to override defaults
├── .gitignore
└── README.md
```

---

## Getting started

### Prerequisites

1. **Docker Desktop** installed and running — https://www.docker.com/products/docker-desktop/
2. On Windows, enable WSL 2 when prompted

### Run it

From the project folder:

```bash
docker compose up --build
```

Then open **http://localhost:8000** in your browser.

The container appears in Docker Desktop as `softreq` with a green healthcheck dot once it's running.

### Default login accounts (seeded automatically)

| Role | Email | Password |
|---|---|---|
| Requester | requester@svcte.edu | password |
| Approver | approver@svcte.edu | password |
| Admin | admin@svcte.edu | password |

---

## Day-to-day commands

```bash
# Start in the background
docker compose up -d

# Stream logs (useful for debugging template errors)
docker compose logs -f web

# Stop
docker compose down

# Stop AND wipe the database (fresh seed on next start)
docker compose down -v && rm -rf data/

# Open a shell inside the running container
docker compose exec web bash

# Rebuild after editing Dockerfile or requirements.txt
docker compose up --build
```

Edits in `./app/`, `./templates/`, and `./static/` **do not** need a rebuild — uvicorn auto-reloads on file change. Only rebuild when `Dockerfile` or `requirements.txt` changes.

---

## Working in VS Code

Install the **Dev Containers** extension, open the project folder, then from the command palette choose **"Dev Containers: Reopen in Container."** VS Code attaches to the running container with Python tooling, IntelliSense, and breakpoints all working.

---

## How the routes work

| Method | Route | What it does |
|---|---|---|
| GET | `/` | Landing / login page (redirects to dashboard if logged in) |
| POST | `/login` | Authenticate with email + password |
| GET | `/logout` | Clear session cookie |
| GET | `/dashboard` | List current user's purchase requests + stats |
| GET | `/new-request` | Form to create a new request |
| POST | `/new-request` | Submit the request (justification must be ≥ 20 chars) |
| GET | `/docs` | FastAPI auto-generated API documentation |
| GET | `/health` | Healthcheck endpoint used by Docker |

---

## Team split

- **Infrastructure & container** — Docker setup, `docker-compose.yml`, `Dockerfile`, devcontainer config, deployment
- **Application code & frontend** — `app/main.py`, all templates in `templates/`, styles in `static/`

---

## Troubleshooting

**Internal Server Error in the browser** — usually a missing template or a variable the template expects but didn't receive. Check `docker compose logs -f web` for the Python traceback.

**Port 8000 already in use** — change the host port in `docker-compose.yml`:
```yaml
ports:
  - "8080:8000"   # now accessible at http://localhost:8080
```

**Changes to `app/` or `templates/` aren't showing up** — confirm the volume mounts in `docker-compose.yml` include those folders:
```yaml
volumes:
  - ./app:/code/app
  - ./templates:/code/templates
  - ./static:/code/static
  - ./data:/code/data
```

**"Cannot connect to the Docker daemon"** — Docker Desktop isn't running. Launch it and wait for the whale icon to stop animating.

**Container shows unhealthy (red dot) in Docker Desktop** — the app's `/health` endpoint isn't responding. Check the logs for a startup error.

**Forgot a password** — all seeded accounts use `password`. To reset the DB entirely, run `docker compose down -v && rm -rf data/` and restart.

---

## Security note (for production, if this ever leaves local dev)

This app is fine for a school project on local machines, but before deploying it anywhere real:

- Passwords are hashed with plain SHA-256 — replace with `bcrypt` or `argon2`
- Sessions are stored in memory — they're wiped on every container restart. Use a real session store (Redis) or signed JWTs
- Swap SQLite for Postgres (already documented in `docker-compose.yml` as a commented example)
- Add HTTPS via a reverse proxy (Caddy, nginx, or Traefik)
- Add CSRF protection on the form submissions
- Rate-limit `/login` to prevent brute force

---

## License

School project — not currently licensed for external use.
