# SwagMonitor

SwagMonitor — это self-hosted система мониторинга VPS-серверов и сервисов с веб-панелью, Telegram-ботом и хранением истории в PostgreSQL.

Проект подходит для личных VPS, небольших продакшен-проектов и домашней инфраструктуры, когда нужен понятный мониторинг без перегруженного enterprise-стека:

- мониторинг доступности VPS по ICMP ping;
- проверки HTTP/HTTPS, TCP-портов и SSL-сертификатов;
- алерты и recovery-уведомления в Telegram;
- история статусов в виде цветных прямоугольников в стиле Uptime Kuma;
- тёмная админ-панель с автообновлением;
- встроенная авторизация пользователей и безопасное развёртывание на VPS.

## Что умеет проект

### Мониторинг серверов

- ICMP ping до VPS;
- средняя, минимальная и максимальная задержка;
- packet loss;
- jitter;
- определение статусов `online`, `degraded`, `offline`, `unknown`;
- история проверок для отображения uptime и статус-полосы.

### Мониторинг сервисов

- HTTP/HTTPS-проверки сайтов;
- проверка HTTP status code;
- измерение времени ответа;
- TCP-проверки стандартных и пользовательских портов;
- проверка срока действия SSL-сертификата.

### Алерты и инциденты

- уведомления о проблемах и восстановлении;
- пороги `warning` и `critical`;
- защита от ложных срабатываний через `N` неудачных проверок подряд;
- mute-режим для сервера;
- журнал alert-событий и список инцидентов.

### Веб-панель

- overview-страница со всеми мониторами;
- строки серверов и сервисов с текущим статусом;
- uptime за `24h / 7d / 30d`;
- история в виде цветных прямоугольников;
- страница отдельного сервера;
- тёмная тема;
- автообновление интерфейса каждые 15 секунд.

### Telegram-бот

- русскоязычное меню и кнопки;
- выбор сервера через inline-кнопки, без ручного ввода имени;
- просмотр статуса, истории, портов и алертов;
- добавление сервера прямо через Telegram;
- работа в группах и в конкретных Telegram topics;
- mute/unmute уведомлений;
- ручная SSL-проверка домена.

## Технологии

### Backend

- Python 3.12+
- FastAPI
- SQLAlchemy 2.x
- Alembic
- PostgreSQL
- APScheduler
- Pydantic Settings

### Telegram

- aiogram 3

### Frontend

- React
- Vite
- Tailwind CSS

### Infra

- Docker
- Docker Compose
- Nginx

## Архитектура

Проект разделён на три основных приложения:

- `backend` — REST API, бизнес-логика, авторизация, фоновые проверки и работа с БД;
- `bot` — Telegram-бот, который использует ту же базу данных и те же сущности мониторинга;
- `frontend` — веб-панель для обзорного экрана и просмотра серверов.

Проверки запускаются в фоне через `APScheduler`. Результаты сохраняются в PostgreSQL, откуда их читают и API, и бот, и интерфейс.

## Структура проекта

```text
.
|-- backend/
|   |-- app/
|   |   |-- api/          # FastAPI routes и auth dependencies
|   |   |-- core/         # конфиг приложения
|   |   |-- db/           # подключение к БД
|   |   |-- models/       # SQLAlchemy модели
|   |   |-- schemas/      # Pydantic схемы
|   |   |-- services/     # мониторинг, дашборд, алерты, auth
|   |   |-- tasks/        # scheduler
|   |   `-- utils/        # ping/http/tcp/ssl helper-функции
|   |-- Dockerfile
|   `-- requirements.txt
|-- bot/
|   |-- Dockerfile
|   |-- handlers.py       # Telegram handlers
|   |-- keyboards.py      # reply/inline keyboards
|   |-- main.py           # точка входа бота
|   |-- services.py       # форматирование и доступ к данным
|   `-- states.py         # FSM для мастера добавления сервера
|-- frontend/
|   |-- src/
|   |   |-- api/
|   |   |-- components/
|   |   |-- hooks/
|   |   `-- pages/
|   |-- Dockerfile
|   `-- nginx.conf
|-- migrations/
|   `-- versions/
|-- scripts/              # локальный запуск на Windows без Docker
|-- .env.example
|-- alembic.ini
|-- docker-compose.yml
`-- README.md
```

## Как это выглядит для пользователя

В панели каждый сервер и сервис отображаются отдельной строкой:

- текущий статус;
- uptime за 24 часа, 7 дней и 30 дней;
- строка истории из маленьких прямоугольников;
- быстрые действия;
- карточка подробностей для конкретного сервера.

Цвета истории:

- зелёный — всё работает;
- красный — недоступно;
- жёлтый — деградация;
- серый — нет данных.

## Быстрый старт на VPS через Docker Compose

### 1. Клонировать проект

```bash
git clone <YOUR_REPOSITORY_URL> swagmonitor
cd swagmonitor
```

### 2. Подготовить `.env`

```bash
cp .env.example .env
```

Минимально нужно заполнить:

```env
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_ADMIN_CHAT_IDS=123456789

AUTH_ENABLED=true
AUTH_BOOTSTRAP_USERNAME=admin
AUTH_BOOTSTRAP_PASSWORD=CHANGE_THIS_TO_A_LONG_RANDOM_PASSWORD
```

Для отправки алертов в группу и конкретный topic можно указать цель в формате:

```env
TELEGRAM_ADMIN_CHAT_IDS=-1001234567890:42
```

Где:

- `-1001234567890` — `chat_id` группы;
- `42` — `topic_id` нужной темы.

Если хочешь дополнительную внешнюю защиту панели до экрана логина:

```env
PANEL_BASIC_AUTH_ENABLED=true
PANEL_AUTH_USER=outeradmin
PANEL_AUTH_PASSWORD=ANOTHER_LONG_RANDOM_PASSWORD
```

### 3. Запустить стек

```bash
docker compose up --build -d
```

### 4. Открыть панель

- веб-панель: `http://<IP_СЕРВЕРА>:3000`
- API внутри VPS: `http://127.0.0.1:8000/docs`

Важно: по умолчанию в `docker-compose.yml`:

- `frontend` опубликован наружу на `3000`;
- `backend` доступен только на `127.0.0.1:8000`;
- `PostgreSQL` доступен только на `127.0.0.1:5432`.

Это сделано специально для безопасности.

### 5. Войти в панель

При первом запуске backend создаст bootstrap-админа из `.env`. Используй:

- `AUTH_BOOTSTRAP_USERNAME`
- `AUTH_BOOTSTRAP_PASSWORD`

После входа можно создать дополнительных пользователей прямо из панели.

## Авторизация и безопасность

SwagMonitor уже включает базовые меры защиты для публичного VPS.

### Встроенная авторизация

- отдельная страница логина;
- сессионные `HttpOnly` cookie;
- bootstrap-админ из `.env`;
- поддержка нескольких пользователей;
- logout из интерфейса.

### Дополнительный внешний слой

При необходимости можно включить HTTP Basic Auth на уровне Nginx:

```env
PANEL_BASIC_AUTH_ENABLED=true
PANEL_AUTH_USER=outeradmin
PANEL_AUTH_PASSWORD=very_strong_password
```

### Что важно сделать перед публикацией

- обязательно смени все дефолтные пароли;
- не оставляй `AUTH_BOOTSTRAP_PASSWORD=change_me_now`;
- используй сложный пароль для панели;
- ограничь доступ к `3000` через firewall, если панель не нужна публично;
- при продакшен-развёртывании добавь HTTPS через внешний reverse proxy.

## Локальный запуск на Windows без Docker

Если хочешь сначала погонять проект у себя на компьютере, можно работать без контейнеров.

### Требования

- Python 3.12+
- Node.js 20+
- PostgreSQL

### 1. Создать БД

Открой `psql` или `pgAdmin` и создай базу:

```sql
CREATE DATABASE monitoringswagbot;
CREATE USER monitor WITH PASSWORD 'monitor';
GRANT ALL PRIVILEGES ON DATABASE monitoringswagbot TO monitor;
\c monitoringswagbot
GRANT USAGE, CREATE ON SCHEMA public TO monitor;
ALTER SCHEMA public OWNER TO monitor;
```

### 2. Подготовить `.env`

Скопируй `.env.example` в `.env` и для локального PostgreSQL укажи:

```env
DATABASE_URL=postgresql+asyncpg://monitor:monitor@127.0.0.1:5432/monitoringswagbot
ALEMBIC_DATABASE_URL=postgresql+psycopg://monitor:monitor@127.0.0.1:5432/monitoringswagbot
```

Если бот пока не нужен, можно не запускать его, но токен потом всё равно пригодится для алертов.

### 3. Запустить backend

Из корня проекта:

```powershell
.\scripts\run_backend.ps1
```

### 4. Запустить frontend

Во втором окне PowerShell:

```powershell
.\scripts\run_frontend.ps1
```

### 5. Запустить Telegram-бота

Опционально, в третьем окне:

```powershell
.\scripts\run_bot.ps1
```

### 6. Или поднять backend + frontend вместе

```powershell
.\scripts\run_local.ps1
```

После запуска:

- панель: `http://localhost:3000`
- API docs: `http://127.0.0.1:8000/docs`

## Telegram-бот

Бот уже адаптирован под ежедневное использование, а не только под raw-команды.

### Что умеет бот

- показать общий статус мониторинга;
- открыть список серверов кнопками;
- выбрать сервер и посмотреть детали;
- показать ping, историю и проверки портов;
- добавить новый сервер через пошаговый мастер;
- приглушить уведомления;
- проверить SSL домена вручную.

### Команды

- `/start` — открыть главное меню;
- `/help` — краткая справка;
- `/status` — общий статус мониторинга;
- `/servers` — список серверов с кнопками выбора;
- `/server` — выбрать сервер и открыть детали;
- `/ping` — выбрать сервер и посмотреть ping;
- `/history` — выбрать сервер и открыть историю;
- `/ports` — выбрать сервер и показать TCP/HTTP/SSL-проверки;
- `/addserver` — добавить сервер прямо через Telegram;
- `/alerts` — последние alert-события;
- `/mute` — приглушить уведомления для сервера;
- `/unmute` — снова включить уведомления;
- `/chatinfo` — показать `chat_id` и `topic_id` текущего чата или темы;
- `/ssl <domain>` — вручную проверить SSL;
- `/cancel` — отменить текущее действие.

### Кнопочная навигация

В боте есть reply и inline-кнопки, поэтому в повседневной работе не нужно постоянно вводить имя сервера руками. Это особенно удобно, если серверов много или они называются длинно.

### Работа в группе и topic

Если бот должен отвечать только в определённой теме Telegram:

1. Добавь бота в группу.
2. Открой нужный topic.
3. Выполни `/chatinfo`.
4. Скопируй значение в формате `chat_id:topic_id`.
5. Укажи его в `.env`:

```env
TELEGRAM_ADMIN_CHAT_IDS=-1001234567890:42
TELEGRAM_ALLOWED_CHAT_IDS=-1001234567890:42
TELEGRAM_ALLOW_PRIVATE_CHATS=true
```

`TELEGRAM_ADMIN_CHAT_IDS` определяет, куда слать алерты.  
`TELEGRAM_ALLOWED_CHAT_IDS` ограничивает, где бот будет принимать команды.  
Если хочешь оставить работу бота ещё и в личке, оставь `TELEGRAM_ALLOW_PRIVATE_CHATS=true`.

## Добавление сервера

### Через веб-панель

Открой overview-страницу, заполни форму справа и создай монитор:

- имя;
- IP или домен;
- описание;
- URL сайта для HTTP-проверки;
- TCP-порты через запятую;
- домен для SSL-проверки.

### Через Telegram

Используй `/addserver` или кнопку `Добавить сервер`.

Бот пошагово спросит:

1. имя сервера;
2. IP или домен;
3. описание;
4. URL сайта;
5. TCP-порты;
6. домен для SSL.

После создания бот автоматически заведёт сервер и дополнительные проверки.

## HTTP API

Если `AUTH_ENABLED=true`, почти все API-маршруты, кроме health и auth, защищены авторизацией.

### Основные маршруты

- `GET /api/health`
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/auth/me`
- `GET /api/auth/users`
- `POST /api/auth/users`
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

Если backend поднят на VPS через стандартный `docker-compose.yml`, Swagger UI доступен только локально на сервере. Для удалённого просмотра используй SSH tunnel или свой reverse proxy.

Пример SSH-туннеля:

```bash
ssh -L 8000:127.0.0.1:8000 user@your-server
```

После этого документация откроется локально по адресу:

```text
http://127.0.0.1:8000/docs
```

## Хранилище данных

PostgreSQL хранит:

- серверы;
- сервисные проверки;
- результаты проверок;
- историю статусов;
- инциденты;
- alert-события;
- пользователей панели;
- auth-сессии.

## Ключевые переменные окружения

| Переменная | Назначение |
|---|---|
| `DATABASE_URL` | строка подключения backend к PostgreSQL |
| `ALEMBIC_DATABASE_URL` | строка подключения Alembic |
| `SCHEDULER_ENABLED` | включает фоновые проверки |
| `SCHEDULER_TICK_SECONDS` | частота прохода scheduler |
| `PING_ATTEMPTS` | число ping-пакетов за одну проверку |
| `DEFAULT_CHECK_INTERVAL_SECONDS` | базовый интервал проверок |
| `DEFAULT_CONSECUTIVE_ALERT_THRESHOLD` | сколько неудач подряд нужно для алерта |
| `HTTP_TIMEOUT_SECONDS` | timeout HTTP/TCP-запросов |
| `SSL_WARNING_DAYS` | за сколько дней предупреждать об истечении SSL |
| `TELEGRAM_BOT_TOKEN` | токен Telegram-бота |
| `TELEGRAM_ADMIN_CHAT_IDS` | список целей для alert-уведомлений, формат `chat_id` или `chat_id:topic_id` |
| `TELEGRAM_ALLOWED_CHAT_IDS` | список разрешённых групп или topics для команд бота |
| `TELEGRAM_ALLOW_PRIVATE_CHATS` | оставить ли работу бота в личных сообщениях |
| `AUTH_ENABLED` | включает встроенную авторизацию панели/API |
| `AUTH_BOOTSTRAP_USERNAME` | логин первого админа |
| `AUTH_BOOTSTRAP_PASSWORD` | пароль первого админа |
| `AUTH_COOKIE_SECURE` | ставить ли `Secure` на auth cookie |
| `PANEL_BASIC_AUTH_ENABLED` | включить внешний Basic Auth для панели |
| `PANEL_AUTH_USER` | логин внешнего Basic Auth |
| `PANEL_AUTH_PASSWORD` | пароль внешнего Basic Auth |

## Типовой сценарий использования

1. Поднять проект на VPS.
2. Войти в веб-панель под bootstrap-админом.
3. Добавить основной VPS и нужные проверки.
4. Подключить Telegram-бота.
5. Проверить, что алерты приходят в Telegram.
6. Следить за uptime, packet loss, latency и инцидентами через overview-экран.

## Что можно развивать дальше

- метрики CPU, RAM, disk и swap через агент на сервере;
- мониторинг Docker-контейнеров;
- публичную status page;
- несколько проектов и групп серверов;
- webhook-интеграции;
- автоматический traceroute при packet loss;
- экспорт отчётов и weekly summary.

## Для разработки

Если ты дорабатываешь проект локально:

- backend и bot используют один и тот же PostgreSQL;
- frontend в dev-режиме проксирует `/api` на локальный FastAPI;
- миграции лежат в `migrations/`;
- после обновления моделей не забывай создавать новую миграцию Alembic.
