# Farm Management API

## اجرای محلی

```powershell
py -3.13 -m venv .venv313
.\.venv313\Scripts\Activate.ps1
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

## ورود و خروج (گام ۴)

- `POST /api/v1/auth/login` با JSON شامل `phone` و `password`، توکن Bearer و `expires_at` برمی‌گرداند.
- `GET /api/v1/auth/me` مشخصات کاربر فعلی را برمی‌گرداند.
- `POST /api/v1/auth/logout` نشست فعلی را باطل می‌کند و پاسخ `204` دارد.

برای دو مسیر آخر، هدر `Authorization: Bearer <access_token>` را بفرستید.
درخواست بدون توکن معتبر یا با رمز نادرست `401` می‌گیرد. عمر پیش‌فرض نشست ۲۴ ساعت است
و با `SESSION_TTL_HOURS` تنظیم می‌شود. فقط هش توکن در دیتابیس ذخیره می‌شود.

## Migration

```powershell
alembic upgrade head
```

فایل دیتابیس پیش‌فرض در `data/farm.db` است و در Git ثبت نمی‌شود. مسیر آن را با متغیر محیطی `DATABASE_URL` تغییر دهید.

تعریف جدول‌های دیتابیس در `db.py` نگهداری می‌شود. هر تغییر ساختاری علاوه بر مدل، به Migration جدید نیاز دارد.

اگر VS Code روی `db.py` خطای import نشان داد، از فرمان **Python: Select Interpreter**
مفسر `.venv313/Scripts/python.exe` را انتخاب کنید. تنظیم پیشنهادی آن در
`.vscode/settings.json` نیز ثبت شده است. Python پیش‌فرض این رایانه 3.14 آزمایشی است؛
این پروژه با Python 3.12 یا 3.13 اجرا می‌شود.
