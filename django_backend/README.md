# اسکلت Django مهاجرت

از ریشه پروژه، وابستگی‌های پروژه را در محیط مجازی نصب کنید و سپس اجرا کنید:

```powershell
python -m pip install -e .
python django_backend/manage.py check
python django_backend/manage.py test accounts farms config operations
```

مسیر سلامت `GET /api/v1/health` است. جزئیات محاسبه‌شدهٔ مزرعه و قطعه از مسیرهای GET برمی‌گردند. فهرست و تقویم عملیات از `/api/v1/operations` و `/api/v1/operations/calendar` در دسترس‌اند.

کاشت با نام محصول به‌طور خودکار دوره کشت می‌سازد و تغییر وضعیت کاشت و برداشت آن را به‌روزرسانی می‌کند. در صورت وجود چند دوره فعال، برداشت دوره‌ای را انتخاب می‌کند که شروع واقعی جدیدتری دارد و در صورت برابری، شناسه بزرگ‌تری دارد. با تأیید مالک، هنگام انتقال کاشت با دوره برنامه‌ریزی‌شده، ارتباط پس از انتقال حفظ می‌شود تا تغییرات بعدی هم دوره را به‌روز کنند؛ این مورد استثنای تأییدشده بر متن قرارداد است. با تأیید مالک، اگر دوره قبلاً برداشت شده باشد، بازگرداندن کاشت که باعث نامعتبرشدن تاریخ برداشت شود با ۴۲۲ رد می‌شود تا کاربر ابتدا برداشت را به‌صورت دستی برگرداند. در حذف یا انتقال دوره برنامه‌ریزی‌شده‌ای که عملیات دیگری به آن وصل است، ۴۰۹ برمی‌گردد.

با تغییر تاریخ برنامه‌ریزی یا ورود به وضعیت تکمیل یا لغو، یادآوری‌های ارسال‌نشده لغو می‌شوند. با حذف عملیات، یادآوری‌های وابسته حذف می‌شوند.
برای جلوگیری از دست‌کاری دیتابیس قبلی، مسیر پیش‌فرض SQLite این اسکلت `django_backend/django.sqlite3` است؛ با `DJANGO_DATABASE_PATH` می‌توان آن را تغییر داد. تست‌ها از SQLite در حافظه استفاده می‌کنند.

`CORS_ORIGINS` فهرست مبدأهای اضافی جداشده با کاماست؛ `http://localhost:5173` همیشه مجاز است. `DJANGO_ALLOWED_HOSTS` نیز فهرست نام میزبان‌ها است. مقدار پیش‌فرض `DJANGO_SECRET_KEY` فقط برای توسعه است؛ برای محیط مستقرشده یک مقدار محرمانه اختصاصی تنظیم کنید. `DJANGO_DEBUG=true` صرفاً برای توسعه است.

عمر نشست با `SESSION_TTL_HOURS` (پیش‌فرض ۲۴، بین ۱ تا ۷۲۰ ساعت) تنظیم می‌شود. محدودیت ورود حداکثر ۱۰ تلاش در هر ۱۰ دقیقه برای هر IP اتصال مستقیم است؛ کش پیش‌فرض محلی و مختص هر پردازه است. پیش از استقرار چندپردازه باید محدودکننده مشترک و پیکربندی امن پروکسی اضافه شود. این اسکلت هنوز آماده انتشار عمومی نیست.

## دادهٔ آزمایشی و اتصال فرانت‌اند

از ریشهٔ مخزن اجرا کنید:

```powershell
New-Item -ItemType Directory -Force -Path data | Out-Null
$env:DJANGO_DATABASE_PATH = Join-Path (Resolve-Path .).Path 'data/django-demo.sqlite3'
$env:DJANGO_DEMO_PASSWORD = Read-Host 'Choose a development password (8–128 characters)'
python django_backend/manage.py migrate
python django_backend/manage.py seed_development
python django_backend/manage.py runserver 127.0.0.1:8000
```

کاربر آزمایشی با شمارهٔ `09123456789` و رمز انتخاب‌شده وارد می‌شود. Seed روی دیتابیس خالی یک کاربر، سه مزرعه، شش قطعه و ۳۰ عملیات می‌سازد. راه‌اندازی و تست اتصال فرانت‌اند در [راهنمای فرانت‌اند](../frontend/README.md) آمده است.

## تمرین انتقال SQLite قدیمی

پس از توقف پردازه‌هایی که روی دیتابیس قدیمی می‌نویسند، یک کپی تهیه کنید. مسیر مقصد باید یک SQLite جداگانه و خالی باشد:

```powershell
Copy-Item -LiteralPath data/farm.db -Destination data/farm-rehearsal-copy.db
$env:DJANGO_DATABASE_PATH = Join-Path (Resolve-Path .).Path 'data/django-rehearsal.sqlite3'
python django_backend/manage.py migrate
python django_backend/manage.py import_legacy_copy --source-copy data/farm-rehearsal-copy.db
```

فرمان کپی مبدأ را فقط برای خواندن باز می‌کند و انتقال را در یک تراکنش انجام می‌دهد. شناسه‌های متنی و کلیدهای خارجی به اعداد تبدیل می‌شوند، قالب هش Argon2 برای Django سازگار می‌شود و نشست‌های قدیمی نیاز به ورود دوباره دارند. پس از تمرین، شمار رکوردها، بررسی کلیدهای خارجی و دسترسی کاربر به داده‌هایش را پیش از هر تغییر مسیر بررسی کنید.
