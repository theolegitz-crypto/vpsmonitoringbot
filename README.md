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

## Next Improvements

- Add authentication for the admin dashboard
- Add charts with selectable time ranges
- Add notification routing per server or per team
- Add bulk edits and maintenance windows
- Add tests for API, alert transitions and monitoring parsers
"# vpsmonitoringbot" 
