# Курсова робота: Інформаційна система диспетчерської служби таксі

Повний монорепозиторій на стеку **FastAPI + SQLAlchemy + Alembic + React (Vite) + PostgreSQL + Docker**.

## Що реалізовано

- Авторизація та ролі: `client`, `driver`, `dispatcher`, `admin`
- Сутності предметної області: `User`, `Client`, `Driver`, `Car`, `Order`, `Review`, `Tariff`
- Автоматичний розрахунок вартості поїздки (відстань + тривалість + тариф + нічний множник)
- Автопризначення вільного водія за класом авто
- Управління статусами водія
- Фільтрація історії замовлень за датою, водієм, вартістю
- Облік автопарку та персоналу (додавання авто, призначення авто водію, блокування користувача)
- Аналітичний звіт: виручка, кількість замовлень, популярні маршрути, активність водіїв
- Багатомовний фронтенд (UA/EN)

## Структура проєкту

- `backend/` — FastAPI API, SQLAlchemy моделі, Alembic міграції, тести
- `frontend/` — React/Vite SPA для демонстрації ролей і бізнес-процесів
- `docker-compose.yml` — оркестрація контейнерів `db`, `backend`, `frontend`

## Швидкий запуск через Docker (рекомендовано)

```powershell
Set-Location 'c:\Users\ASUS\Desktop\Курсова'
docker compose up --build
```

Після старту доступно:
- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`
- PostgreSQL: `localhost:5432` (db: `taxi_dispatch`, user: `taxi_user`)

При старті backend контейнер автоматично:
1. Чекає готовність PostgreSQL.
2. Виконує `alembic upgrade head`.
3. Запускає seed стартових тарифів.
4. Підіймає FastAPI-сервер.

## Запуск backend

1. Перейти в `backend/`
2. Встановити залежності з `requirements.txt`
3. Запустити Alembic міграцію
4. Запустити сервер

Ключові entrypoints:
- API: `http://127.0.0.1:8000`
- Swagger: `http://127.0.0.1:8000/docs`
- Health: `GET /health`

## Запуск frontend

1. Перейти в `frontend/`
2. Встановити npm-залежності
3. Запустити dev-сервер

UI адреса за замовчуванням: `http://localhost:5173`

## Основні API-маршрути

- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/auth/me`
- `POST /api/orders`
- `GET /api/orders`
- `PATCH /api/orders/{order_id}/status`
- `POST /api/orders/review`
- `POST /api/management/cars`
- `GET /api/management/cars`
- `POST /api/management/tariffs`
- `GET /api/management/tariffs`
- `PATCH /api/management/drivers/me/status`
- `PATCH /api/management/drivers/{driver_id}/assign-car`
- `PATCH /api/management/users/{user_id}/block`
- `GET /api/management/reports/summary`

## Бізнес-процеси, покриті системою

1. **Управління замовленнями** — створення заявки, підбір тарифу, оцінка вартості, призначення водія.
2. **Диспетчеризація і моніторинг** — контроль статусу водіїв, керування замовленнями.
3. **Облік автопарку та кадрів** — CRUD-операції над авто/тарифами, призначення авто водію.
4. **Авторизація та профілі** — розмежування прав доступу за ролями.
5. **Аналітика** — звіти за період по доходах, маршрутах і продуктивності.

## Тестування

У `backend/tests/` реалізовані базові тести:
- реєстрація + доступ до профілю
- повний сценарій замовлення з автопризначенням водія
- edge-case: клієнт без телефону

## Відомі обмеження

- Геокодування адрес не підключено до зовнішнього map API: використовується передача координат у заявці.
- UI зроблено демонстраційним (MVP), без складної роле-орієнтованої навігації і без state manager.

## Скидання БД та повторний запуск контейнерів

```powershell
Set-Location 'c:\Users\ASUS\Desktop\Курсова'
docker compose down -v
docker compose up --build
```
