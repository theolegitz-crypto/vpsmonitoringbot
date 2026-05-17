# SwagMonitor

SwagMonitor is a starter project for VPS and service monitoring with:

- FastAPI backend and PostgreSQL storage
- aiogram Telegram bot for commands and alerts
- APScheduler-based background checks
- React + Tailwind dashboard with dark theme
- Docker Compose setup for local deployment

## Architecture

- `backend/app/main.py`: FastAPI entrypoint, API wiring and scheduler startup
- `backend/app/models/`: SQLAlchemy models for servers, checks, results, incidents and alerts
- `backend/app/services/monitoring.py`: ICMP, HTTP, TCP and SSL monitoring flow
- `backend/app/services/alerting.py`: incident lifecycle, recovery logic and Telegram notifications
- `bot/`: Telegram bot commands backed by the same PostgreSQL data
- `frontend/`: dashboard with overview and per-server details
- `migrations/`: Alembic environment and initial schema

## Project Structure

```text
.
|-- backend/
|   |-- app/
|   |   |-- api/
|   |   |-- core/
|   |   |-- db/
|   |   |-- models/
|   |   |-- schemas/
|   |   |-- services/
|   |   |-- tasks/
|   |   `-- utils/
|   |-- Dockerfile
|   `-- requirements.txt
|-- bot/
|   |-- Dockerfile
|   |-- handlers.py
|   |-- main.py
|   `-- services.py
|-- frontend/
|   |-- src/
|   |   |-- api/
|   |   |-- components/
|   |   `-- pages/
|   |-- Dockerfile
|   `-- nginx.conf
|-- migrations/
|   `-- versions/
|-- alembic.ini
|-- docker-compose.yml
`-- .env.example
```

## Monitoring Coverage

- ICMP ping with average, minimum, maximum latency, packet loss and jitter
- HTTP/HTTPS checks with status code validation and response time
- TCP checks for standard or custom ports
- SSL expiration checks with warning and critical behavior
- Consecutive failure threshold before alerts fire
- Recovery alerts after a host or check comes back
- Per-server and per-check mute windows

## API Endpoints

- `GET /api/health`
- `GET /api/dashboard/overview`
- `GET /api/dashboard/incidents`
- `GET /api/servers`
- `POST /api/servers`
- `GET /api/servers/{server_id}`
- `PATCH /api/servers/{server_id}`
- `DELETE /api/servers/{server_id}`
- `POST /api/servers/{server_id}/mute`
- `POST /api/servers/{server_id}/unmute`
- `POST /api/servers/{server_id}/run-check`
- `GET /api/servers/{server_id}/history`
- `POST /api/servers/{server_id}/checks`
- `PATCH /api/servers/checks/{check_id}`
- `DELETE /api/servers/checks/{check_id}`
- `POST /api/servers/checks/{check_id}/run`

## Telegram Commands

- `/start`
- `/status`
- `/servers`
- `/server <name>`
- `/alerts`
- `/history <name>`
- `/mute <name> <duration>`
- `/unmute <name>`
- `/ping <name>`
- `/ssl <domain>`

## Quick Start

1. Copy `.env.example` to `.env` and fill in `TELEGRAM_BOT_TOKEN` and `TELEGRAM_ADMIN_CHAT_IDS`.
2. Build and start the stack:

   ```bash
   docker compose up --build
   ```

3. Open the services:

   - Dashboard: `http://localhost:3000`
   - Backend API docs: `http://localhost:8000/docs`

4. Add your first server from the dashboard or via `POST /api/servers`.

## VPS Security

SwagMonitor now supports built-in panel authentication with session cookies and users stored in PostgreSQL.

### Required internal auth settings

Before first startup set the bootstrap admin credentials in `.env`:

```env
AUTH_ENABLED=true
AUTH_BOOTSTRAP_USERNAME=admin
AUTH_BOOTSTRAP_PASSWORD=replace_with_a_long_random_password
```

On first startup the backend creates this admin user automatically. After login you can create more users from the web panel.

### Optional extra outer protection

You can also keep an additional HTTP Basic Auth layer in front of the panel:

```env
PANEL_BASIC_AUTH_ENABLED=true
PANEL_AUTH_USER=admin
PANEL_AUTH_PASSWORD=replace_with_a_long_random_password
```

Security changes included in `docker-compose.yml`:

- the web panel requires internal login
- optional extra Basic Auth can protect it before the login page
- PostgreSQL on `5432` is bound only to `127.0.0.1`
- backend API on `8000` is bound only to `127.0.0.1`

That means external users can no longer access the API directly unless they already have shell access to the VPS or another reverse proxy exposes it.

## Local Development

### Backend

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r backend/requirements.txt
alembic upgrade head
uvicorn backend.app.main:app --reload
```

### Bot

```bash
python -m bot.main
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Windows Run Without Docker

This mode keeps everything on your computer directly instead of containers.

### What you need

- Python 3.12+
- Node.js 20+
- PostgreSQL installed locally

### 1. Create the database

Create a local database and user in PostgreSQL, for example:

```sql
CREATE DATABASE monitoringswagbot;
CREATE USER monitor WITH PASSWORD 'monitor';
GRANT ALL PRIVILEGES ON DATABASE monitoringswagbot TO monitor;
\c monitoringswagbot
GRANT USAGE, CREATE ON SCHEMA public TO monitor;
ALTER SCHEMA public OWNER TO monitor;
```

### 2. Prepare `.env`

Copy `.env.example` to `.env` and for local PostgreSQL use:

```env
DATABASE_URL=postgresql+asyncpg://monitor:monitor@127.0.0.1:5432/monitoringswagbot
ALEMBIC_DATABASE_URL=postgresql+psycopg://monitor:monitor@127.0.0.1:5432/monitoringswagbot
```

If you do not need Telegram right now, you can leave `TELEGRAM_BOT_TOKEN` empty and simply not start the bot.

### 3. Run locally

In PowerShell from the project root:

```powershell
.\scripts\run_backend.ps1
```

In a second PowerShell window:

```powershell
.\scripts\run_frontend.ps1
```

Optional, in a third window:

```powershell
.\scripts\run_bot.ps1
```

Or start backend + frontend together:

```powershell
.\scripts\run_local.ps1
```

### 4. Open the app

- Dashboard: `http://localhost:3000`
- API docs: `http://127.0.0.1:8000/docs`

The frontend dev server now proxies `/api` to local FastAPI automatically, so no extra frontend env config is needed.

## Next Improvements

- Add authentication for the admin dashboard
- Add charts with selectable time ranges
- Add notification routing per server or per team
- Add bulk edits and maintenance windows
- Add tests for API, alert transitions and monitoring parsers
"# vpsmonitoringbot" 
