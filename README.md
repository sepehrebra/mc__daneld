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

## ثبت‌نام (گام ۳)

پیش از استفاده از API، Migration را اجرا کنید. `POST /api/v1/auth/register` یک بدنهٔ JSON
با `full_name`، `phone`، `password` و `email` اختیاری می‌گیرد. نمونه:

```json
{"full_name":"نام کاربر","phone":"09123456789","password":"a-long-password","email":"user@example.com"}
```

شماره به قالب بین‌المللی E.164 ذخیره می‌شود. پاسخ موفق `201` و بدون رمز یا هش رمز است؛
شماره یا ایمیل تکراری `409` و ورودی نامعتبر `422` برمی‌گرداند.

## Migration

```powershell
alembic upgrade head
```

فایل دیتابیس پیش‌فرض در `data/farm.db` است و در Git ثبت نمی‌شود. مسیر آن را با متغیر محیطی `DATABASE_URL` تغییر دهید.

تعریف جدول‌های دیتابیس در `db.py` نگهداری می‌شود. هر تغییر ساختاری علاوه بر مدل، به Migration جدید نیاز دارد.
