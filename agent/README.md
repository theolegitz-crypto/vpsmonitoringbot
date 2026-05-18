# SwagMonitor Agent

Небольшой Python-агент для отправки системных метрик VPS и снимков Docker-контейнеров в backend SwagMonitor.

## Что отправляет агент

- CPU usage
- RAM usage
- swap usage
- disk usage
- load average
- network RX/TX
- uptime
- список Docker-контейнеров
- restart count контейнеров
- health status контейнеров
- CPU/RAM контейнеров
- speed test download/upload/ping по запросу из панели или Telegram

## Как это работает

Агент запускается прямо на VPS и с заданным интервалом отправляет heartbeat в:

`POST /api/agent/ingest`

Backend сохраняет эти данные в PostgreSQL, показывает их на странице сервера и использует для alert-сценариев по контейнерам.

## Быстрый запуск на VPS

1. Перейди в каталог проекта.
2. Создай отдельное виртуальное окружение для агента.
3. Установи зависимости.
4. Подготовь `.env.agent`.
5. Запусти агент.

Пример:

```bash
cd /opt/vpsmonitoringbot
python3 -m venv .venv-agent
source .venv-agent/bin/activate
pip install -r agent/requirements.txt
cp agent/.env.agent.example .env.agent
python agent/main.py
```

## Обязательные переменные

- `AGENT_BACKEND_URL` — URL backend, обычно `http://127.0.0.1:8000`
- `AGENT_SHARED_TOKEN` — тот же токен, что указан в backend `.env` как `AGENT_SHARED_TOKEN`
- `AGENT_SERVER_NAME` или `AGENT_SERVER_ID` — какой сервер в базе обновлять

## Пример `.env.agent`

```env
AGENT_BACKEND_URL=http://127.0.0.1:8000
AGENT_SHARED_TOKEN=replace_with_long_random_token
AGENT_SERVER_NAME=vps1
AGENT_INTERVAL_SECONDS=30
AGENT_ENABLE_DOCKER=true
AGENT_SPEEDTEST_ENABLED=true
AGENT_SPEEDTEST_TIMEOUT_SECONDS=180
AGENT_DISK_PATH=/
```

## systemd

Пример unit-файла:

```ini
[Unit]
Description=SwagMonitor Agent
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/opt/vpsmonitoringbot
EnvironmentFile=/opt/vpsmonitoringbot/.env.agent
ExecStart=/opt/vpsmonitoringbot/.venv-agent/bin/python /opt/vpsmonitoringbot/agent/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

После сохранения:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now swagmonitor-agent
sudo systemctl status swagmonitor-agent
```

## Замечания

- Для мониторинга контейнеров агенту нужен доступ к Docker socket.
- Если Docker на VPS не используется, оставь `AGENT_ENABLE_DOCKER=false`.
- Для speed test агент использует `speedtest-cli`; тест запускается только когда ты нажимаешь кнопку в панели или в Telegram.
- Для максимально точных метрик VPS агент лучше запускать на хосте, а не внутри контейнера.
