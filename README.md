# Farm Management API

## اجرای محلی

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
uvicorn app.main:app --reload
```

پس از اجرا، `GET /health` وضعیت سرویس و اتصال SQLite را بررسی می‌کند.

## Migration

```powershell
alembic upgrade head
```

فایل دیتابیس پیش‌فرض در `data/farm.db` است و در Git ثبت نمی‌شود. مسیر آن را با متغیر محیطی `DATABASE_URL` تغییر دهید.
