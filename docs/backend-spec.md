# مستند پیاده‌سازی بک‌اند «کشاورزیار»

این مستند برای یک هوش مصنوعی (یا برنامه‌نویس) نوشته شده که باید بک‌اند برنامه‌ی «کشاورزیار» را پیاده‌سازی کند. فرانت‌اند کامل است و فعلاً با داده‌ی آزمایشی کار می‌کند. هدف: بک‌اندی بسازی که دقیقاً با قرارداد زیر کار کند تا فرانت‌اند فقط با خاموش کردن حالت آزمایشی (`USE_MOCK = false`) به آن وصل شود.

**قواعد استفاده از این مستند**
- این مستند منبع حقیقت است. هر جا با «مدل داده» (بخش ۳) فرق دارد، بخش ۴ («تغییرات لازم نسبت به قواعد اولیه») مقدم است.
- نام فیلدها، مسیرها و کدهای خطا را دقیقاً مثل این مستند بنویس. فرانت‌اند آن‌ها را سخت‌کد کرده است.
- هر جا چیزی مشخص نشده، ساده‌ترین رفتار معقول را انتخاب کن و در پایان کارت فهرستش کن.

---

## ۱. محصول در یک نگاه
اپلیکیشن وب فارسی و راست‌به‌چپ، موبایل‌اول، برای کشاورزان خرده‌مالک. کاربر ثبت‌نام می‌کند، **مزرعه** و **قطعه‌ی زراعی** تعریف می‌کند و **عملیات** (کاشت، آبیاری، کوددهی، سم‌پاشی، برداشت، سایر) را برنامه‌ریزی یا ثبت می‌کند. برنامه تقویم شمسی، شمارش «اقدام امروز» و «عقب‌افتاده» و جست‌وجو در سوابق دارد.

نکته: تقویم شمسی **فقط در فرانت‌اند** است. بک‌اند همه‌جا فقط تاریخ میلادی ISO می‌گیرد و می‌دهد.

## ۲. قراردادهای کلی
| موضوع | قرارداد |
|---|---|
| آدرس پایه | `/api/v1` (فرانت‌اند با `BASE_URL` تنظیمش می‌کند) |
| قالب | JSON، UTF-8، هدر `Content-Type: application/json` |
| احراز هویت | هدر `Authorization: Bearer <access_token>` برای همه‌ی مسیرها به‌جز `register` و `login` |
| شناسه‌ها | عدد صحیح (`id`) |
| تاریخ | رشته‌ی `YYYY-MM-DD` میلادی (مثل `2026-10-30`) |
| ساعت برنامه‌ریزی | `HH:mm` (فرانت‌اند `"08:30"` می‌فرستد؛ در پاسخ `"08:30"` یا `"08:30:00"` هر دو قابل‌قبول است) |
| زمان لحظه‌ای | ISO 8601 با UTC و `Z` (مثل `2026-10-30T08:30:00Z`) |
| منطقه‌ی زمانی | هر مزرعه `timezone` دارد (پیش‌فرض `Asia/Tehran`). «امروز»، `scheduled_date/time` و `completed_date` همه به وقت **مزرعه** تفسیر می‌شوند، نه UTC |
| متن | قبل از ذخیره `trim` شود. فیلدهای اختیاریِ خالی (`""`) مثل `null` رفتار کنند |
| CORS | مبدأ فرانت‌اند (در توسعه `http://localhost:5173`)، متدهای `GET POST PATCH DELETE OPTIONS`، هدرهای `Authorization` و `Content-Type` |

**کدهای خطا** (فرانت‌اند فقط کد را می‌خواند و متن فارسی خودش را نشان می‌دهد؛ بدنه‌ی خطا آزاد است، پیشنهاد: `{"detail": "..."}`)
- `401`: توکن نبود، نامعتبر، باطل‌شده یا منقضی (برای `login` یعنی شماره یا رمز اشتباه). فرانت‌اند با `401` نشست را پاک می‌کند و به صفحه‌ی ورود می‌رود.
- `404`: منبع وجود ندارد **یا متعلق به کاربر دیگری است** (هرگز `403` نده تا وجود منبع لو نرود).
- `409`: تکراری بودن (شماره یا ایمیل کاربر؛ نام یا کد قطعه در یک مزرعه).
- `422`: ورودی نامعتبر.

## ۳. مدل داده (SQLite)
ساختار زیر را از مالک پروژه گرفته‌ام و عیناً رعایت کن، مگر مواردی که در بخش ۴ تغییر می‌کند.

**users**: `id, full_name, phone, email, password_hash, is_active, created_at, updated_at`
- `phone` اجباری و یکتا؛ پیش از ذخیره به E.164 تبدیل شود. `email` اختیاری و یکتا (NULL مجاز). `is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1))`.

**auth_sessions**: `id, user_id, token_hash, expires_at, revoked_at, created_at, updated_at`
- `user_id` کلید خارجی اجباری به `users.id`. فقط هش SHA-256 توکن تصادفی و یکتا ذخیره می‌شود؛ توکن خام فقط هنگام ورود برگردانده می‌شود. عمر نشست ۲۴ ساعت (تنظیم با `SESSION_TTL_HOURS`). خروج `revoked_at` را ثبت می‌کند و همان توکن بلافاصله از کار می‌افتد.

**farms**: `id, owner_id, name, province, city, address, latitude, longitude, timezone, description, created_at, updated_at`
- `owner_id` کلید خارجی اجباری به `users.id`. `timezone TEXT NOT NULL DEFAULT 'Asia/Tehran'` و باید IANA معتبر باشد. عرض جغرافیایی بین -90 و 90، طول بین -180 و 180. مختصات یا هر دو NULL‌اند یا هر دو مقدار دارند.

**plots**: `id, farm_id, name, code, area_m2, soil_type, description, created_at, updated_at`
- `farm_id` کلید خارجی اجباری. `area_m2 REAL NOT NULL CHECK (area_m2 > 0)`. `UNIQUE(farm_id, name)`. `code` اختیاری ولی در صورت وجود `UNIQUE(farm_id, code)`.

**crop_seasons**: `id, plot_id, crop_name, variety, start_date, actual_start_date, expected_end_date, actual_end_date, status, notes, created_at, updated_at`
- `plot_id` کلید خارجی اجباری. `status TEXT NOT NULL DEFAULT 'planned' CHECK (status IN ('planned','active','completed','cancelled'))`. پایان برنامه‌ریزی‌شده نباید پیش از شروع برنامه‌ریزی‌شده باشد؛ پایان واقعی نباید پیش از شروع واقعی باشد؛ ثبت پایان واقعی بدون شروع واقعی مجاز نیست. دوره‌های هم‌پوشان مجازند.

**operations**: `id, plot_id, crop_season_id, created_by, title, operation_type, description, scheduled_date, scheduled_time, completed_at, status, result_notes, created_at, updated_at`
- `plot_id` و `created_by` اجباری؛ `crop_season_id` اختیاری و در صورت وجود باید متعلق به همان `plot_id` باشد.
- `operation_type CHECK IN ('planting','irrigation','fertilizing','spraying','harvesting','other')`.
- `status TEXT NOT NULL DEFAULT 'planned' CHECK IN ('planned','in_progress','completed','cancelled')`.
- اگر `status='completed'` آنگاه `completed_at` اجباری است؛ در غیر این صورت باید NULL باشد.
- `scheduled_date` و `scheduled_time` با منطقه‌ی زمانی مزرعه تفسیر می‌شوند.

**reminders**: `id, operation_id, recipient_id, remind_at, channel, status, sent_at, read_at, attempt_count, last_error, created_at, updated_at`
- `channel` فقط `'in_app'`؛ `status IN ('pending','processing','sent','failed','cancelled')`؛ `attempt_count >= 0`. گیرنده باید مالک مزرعه‌ی عملیات باشد. `remind_at` به UTC تبدیل شود. `last_error` در پاسخ API برنمی‌گردد. تغییر موعد، تکمیل یا لغو عملیات، یادآوری‌های ارسال‌نشده‌ی آن را `cancelled` می‌کند (جایگزین خودکار ساخته نمی‌شود).
- **صفحه‌های فعلی از `reminders` استفاده نمی‌کنند** (بخش ۱۰)؛ فقط قاعده‌ی لغو را هنگام تغییر عملیات رعایت کن.

## ۴. تغییرات لازم نسبت به قواعد اولیه‌ی دیتابیس
رابط کاربری جدید (کارت و مودال ویرایش عملیات) با دو قاعده‌ی اولیه سازگار نیست. این‌ها را عوض کن:

1. **گذار وضعیت آزاد است.** از هر وضعیتی به هر وضعیت دیگر (`planned`, `in_progress`, `completed`, `cancelled`) می‌شود رفت، از جمله بازگشت از `completed` و `cancelled` به `planned`. (قید «وضعیت‌های پایانی بازگشت ندارند» حذف می‌شود.)
2. **`completed_at` و ویرایش تاریخ انجام.** کاربر می‌تواند تاریخ انجام را در مودال تعیین کند. API یک فیلد `completed_date` (تاریخ، به وقت مزرعه) می‌گیرد و می‌دهد:
   - اگر `status` به `completed` برود و `completed_date` نیامده باشد: `completed_at = اکنون (UTC)`.
   - اگر `completed_date` برابر «امروز به وقت مزرعه» باشد: `completed_at = اکنون`. اگر روز دیگری باشد: `completed_at = ساعت ۱۲:۰۰ به وقت مزرعه‌ی آن روز` (تبدیل‌شده به UTC).
   - `completed_date` در پاسخ همیشه = بخش تاریخِ `completed_at` به وقت مزرعه (یا `null` اگر انجام نشده).
   - اگر وضعیت از `completed` به چیز دیگری برود، `completed_at = NULL`.
   - ارسال `completed_date` همراه وضعیتی که `completed` نیست (و عملیات هم از قبل `completed` نیست) خطای `422` است.
3. **`scheduled_date` عملیات انجام‌شده هم قابل ویرایش است** (قید «موعد فعالیت پایان‌یافته تغییر نمی‌کند» حذف می‌شود).
4. `result_notes` فعلاً در هیچ صفحه‌ای استفاده نمی‌شود.

## ۵. احراز هویت و مالکیت
- رمز با الگوریتم امن (argon2 یا bcrypt) هش شود. فرانت‌اند حداقل ۸ کاراکتر را اجباری می‌کند؛ سمت سرور هم بررسی کن (حداکثر ۱۲۸).
- فرانت‌اند شماره را همیشه به E.164 ایران می‌فرستد (`+989123456789`)؛ سمت سرور هم اعتبارسنجی و نرمال‌سازی کن (ارقام فارسی و عربی را به انگلیسی تبدیل کن).
- **مالکیت:** هر کاربر فقط به مزرعه‌هایی دسترسی دارد که `farms.owner_id` او باشد و به همه‌ی چیزهای زیرمجموعه‌شان (قطعه، دوره‌ی کشت، عملیات، یادآوری). دسترسی به منبع دیگران `404` بدهد. هنگام ساخت یا ویرایش عملیات، `plot_id` باید متعلق به مزرعه‌ی همین کاربر باشد (وگرنه `404` یا `422`).
- `created_by` عملیات همیشه کاربر احرازشده است و از ورودی گرفته نمی‌شود.

## ۶. API

### ۶.۱ احراز هویت
| مسیر | بدنه | پاسخ |
|---|---|---|
| `POST /auth/register` | `{full_name, phone, password, email?}` | `201` بدون رمز و هش. `409` شماره یا ایمیل تکراری. `422` ورودی نامعتبر |
| `POST /auth/login` | `{phone, password}` | `200 {access_token, token_type:"bearer", expires_at}`؛ `401` اگر اشتباه |
| `GET /auth/me` | ـ | `{id, full_name, phone, email}` (فرانت‌اند فقط `full_name` را در منو نشان می‌دهد) |
| `POST /auth/logout` | ـ | `204`؛ نشست فعلی باطل می‌شود |

بعد از `register` فرانت‌اند فوراً `login` را صدا می‌زند (register توکن نمی‌دهد).

### ۶.۲ مزرعه‌ها
**`GET /farms`** — فهرست سبک مزرعه‌های کاربر (برای لیست‌های انتخاب، لیست مزرعه‌ها و داشبورد)، به ترتیب `id` صعودی:
```json
[{ "id": 1, "name": "مزرعه‌ی گندم", "plots": [{ "id": 11, "name": "قطعه‌ی شمالی" }] }]
```

**`POST /farms`** — `{name, address?, description?}`؛ `name` اجباری و غیرخالی. پاسخ `201` با مزرعه‌ی کامل.

**`GET /farms/{id}`** — جزئیات؛ `404` اگر نبود:
```json
{
  "id": 1, "name": "...", "province": null, "city": null, "address": null,
  "latitude": null, "longitude": null, "timezone": "Asia/Tehran", "description": null,
  "plots": [{
    "id": 11, "name": "قطعه‌ی شمالی", "code": "A1", "area_m2": 20000, "soil_type": null, "description": null,
    "today_count": 1, "overdue_count": 1,
    "current_season": { "crop_name": "گندم", "variety": "پیشتاز", "start_date": "2026-09-23",
                        "actual_start_date": "2026-09-25", "status": "active" },
    "next_operation": { "id": 5, "title": "آبیاری", "operation_type": "irrigation",
                        "scheduled_date": "2026-10-29", "scheduled_time": null },
    "last_irrigation_at": "2026-10-21T08:00:00Z"
  }]
}
```
قطعه‌ها به ترتیب `id` صعودی. تعریف فیلدهای محاسبه‌ای در بخش ۷.

**`PATCH /farms/{id}`** — ویرایش جزئی با هر زیرمجموعه‌ای از `{name, province, city, address, latitude, longitude, description}`. `null` یعنی پاک کردن. `name` نباید خالی شود. مختصات: یا هر دو `null` یا هر دو عدد معتبر، وگرنه `422`. پاسخ `200` با مزرعه‌ی کامل.

**`POST /farms/{id}/plots`** — `{name, code?, area_m2, soil_type?, description?}`. `201`. `409` اگر `(farm_id,name)` یا `(farm_id,code)` تکراری باشد. `422` اگر `area_m2 <= 0`.

### ۶.۳ قطعه‌ها
**`GET /plots/{id}`** — جزئیات یک قطعه:
```json
{
  "id": 11, "name": "...", "code": null, "area_m2": 20000, "soil_type": null, "description": null,
  "farm": { "id": 1, "name": "مزرعه‌ی گندم" },
  "today_count": 1, "overdue_count": 1,
  "current_season": { "crop_name": "گندم", "variety": null, "start_date": "...", "actual_start_date": "...", "status": "active" },
  "last_done": { "irrigation": "2026-10-21T08:00:00Z", "fertilizing": null, "spraying": null },
  "next_operations": [ /* حداکثر ۳ آیتم عملیات */ ],
  "recent_operations": [ /* حداکثر ۳ آیتم عملیات */ ]
}
```
**`PATCH /plots/{id}`** — جزئیات: `{name, code, area_m2, soil_type, description}` (`null` = پاک کردن؛ `name` و `area_m2` نباید `null` شوند). `409` برای تکراری بودن، `422` برای `area_m2 <= 0`. پاسخ `200` با قطعه.

### ۶.۴ عملیات
**آیتم عملیات** (شکل یکسان در همه‌ی پاسخ‌ها؛ فرانت‌اند به همه‌ی این فیلدها نیاز دارد):
```json
{
  "id": 7, "title": "آبیاری", "operation_type": "irrigation", "description": null,
  "scheduled_date": "2026-10-29", "scheduled_time": "08:30", "status": "planned",
  "completed_date": null,
  "farm": { "id": 1, "name": "مزرعه‌ی گندم" }, "plot": { "id": 11, "name": "قطعه‌ی شمالی" }
}
```
`farm` از join قطعه به مزرعه می‌آید. `completed_date` فقط وقتی `status="completed"` است مقدار دارد.

**`POST /operations`**
```json
{ "plot_id": 11, "operation_type": "planting", "title": "کاشت گندم",
  "scheduled_date": "2026-10-30", "scheduled_time": "08:30", "description": "...",
  "crop_name": "گندم", "variety": "پیشتاز", "status": "planned", "completed_date": "2026-10-30" }
```
- اجباری: `plot_id`, `operation_type`, `scheduled_date`. بقیه اختیاری.
- `title` اگر نیامد: برچسب فارسی نوع (`planting` کاشت، `irrigation` آبیاری، `fertilizing` کوددهی، `spraying` سم‌پاشی، `harvesting` برداشت، `other` سایر).
- `status` پیش‌فرض `planned`. `completed_date` طبق قاعده‌ی بخش ۴.
- `crop_name` و `variety` فقط برای `planting` معنی دارند (بخش ۸).
- پاسخ `201` با آیتم عملیات.

**`PATCH /operations/{id}`** — ویرایش جزئی. فرانت‌اند **فقط فیلدهای تغییرکرده** را می‌فرستد، از میان:
`operation_type, title, plot_id, scheduled_date, scheduled_time, description, status, completed_date`. `null` برای `scheduled_time` و `description` یعنی پاک کردن. پاسخ `200` با آیتم عملیات. نمونه‌ی ارسال‌های واقعی:
- «انجام شد» از منو: `{"status":"completed"}`
- «لغو» از منو: `{"status":"cancelled"}`
- ویرایش در مودال: مثلاً `{"scheduled_date":"2026-11-02","status":"completed","completed_date":"2026-11-01"}`

**`DELETE /operations/{id}`** — `204`. یادآوری‌های وابسته هم حذف شوند.

**`GET /operations`** — جست‌وجو و فهرست. پارامترهای query (همه اختیاری):
| پارامتر | معنی |
|---|---|
| `from`, `to` | بازه‌ی `scheduled_date`، دو سر بسته |
| `farm` | شناسه‌ی مزرعه (از طریق قطعه) |
| `plot` | شناسه‌ی قطعه |
| `status` | یک یا چند وضعیت با کاما، مثل `planned,in_progress` |
| `sort` | `date` (پیش‌فرض): بر اساس `scheduled_date` و سپس `scheduled_time` و `id`. `created`: بر اساس `created_at` نزولی (برای «آخرین ثبت‌شده‌ها») |
| `order` | `asc` یا `desc` (پیش‌فرض `desc`)، فقط برای `sort=date` |
| `limit` | پیش‌فرض ۲۰، حداکثر ۱۰۰ |
| `offset` | پیش‌فرض ۰ |

پاسخ: **آرایه‌ی ساده** از آیتم‌های عملیات (بدون پوشش و بدون شمارنده‌ی کل). مهم: اگر بیشتر از `limit` نتیجه وجود دارد، دقیقاً `limit` آیتم برگردان؛ فرانت‌اند دکمه‌ی «نمایش بیشتر» را وقتی نشان می‌دهد که طول پاسخ برابر ۲۰ باشد. فقط عملیات کاربر جاری.

سه استفاده‌ی واقعی:
- «کارهای پیش رو» (داشبورد): `GET /operations?status=planned,in_progress&order=asc&limit=3` ← نزدیک‌ترین‌ها، **عقب‌افتاده‌ها هم** (چون تاریخ کوچک‌ترند، اول می‌آیند).
- «عملیات‌های اخیر» (صفحه‌ی ثبت عملیات): `GET /operations?limit=5&sort=created`.
- جست‌وجو در سوابق: همه‌ی پارامترها، با `limit=20&offset=...`. لینک‌های صفحه‌ی قطعه این دو را می‌فرستند: `status=planned,in_progress&order=asc` و `status=completed`.

**`GET /operations/calendar?from=YYYY-MM-DD&to=YYYY-MM-DD`** — برای تقویم ماهانه (فرانت‌اند بازه‌ی میلادیِ یک ماه شمسی را می‌فرستد، ۲۹ تا ۳۱ روز).
- همه‌ی عملیات‌هایی که **تاریخ مؤثرشان** در بازه است. تاریخ مؤثر = `completed_date` اگر `status="completed"`، وگرنه `scheduled_date`. (عملیاتی که ۴ فروردین برنامه‌ریزی شد و ۱۰ فروردین انجام شد، فقط در ۱۰ فروردین می‌آید.)
- **همه‌ی وضعیت‌ها شامل `cancelled`** برگردانده شود (تاریخ مؤثر لغوشده = `scheduled_date`).
- بدون صفحه‌بندی؛ اگر بازه بیشتر از ۶۲ روز بود `422`. ترتیب: تاریخ مؤثر، سپس `scheduled_time`، سپس `id`.

## ۷. فیلدهای محاسبه‌ای
تعاریف برای هر قطعه. «امروز» = تاریخ جاری به وقت `timezone` مزرعه. «عملیات باز» = `status IN ('planned','in_progress')`.
- `today_count` = تعداد عملیات باز با `scheduled_date == امروز`.
- `overdue_count` = تعداد عملیات باز با `scheduled_date < امروز`.
- `next_operation` (در `GET /farms/{id}`) = نزدیک‌ترین عملیات باز به ترتیب `scheduled_date`، `scheduled_time`، `id` (**عقب‌افتاده‌ها هم حساب می‌شوند**)؛ اگر نبود `null`. فقط `{id,title,operation_type,scheduled_date,scheduled_time}`.
- `last_irrigation_at` = بزرگ‌ترین `completed_at` میان عملیات `completed` از نوع `irrigation`؛ وگرنه `null`. `last_done.fertilizing` و `last_done.spraying` همین‌طور برای `fertilizing` و `spraying`.
- `next_operations` = تا ۳ عملیات باز، `scheduled_date` صعودی (عقب‌افتاده‌ها اول).
- `recent_operations` = تا ۳ عملیات `completed`، `completed_at` نزولی.
- `current_season` = دوره‌ی کشتِ آن قطعه با `status='active'`؛ اگر نبود جدیدترین دوره با `status='planned'`؛ وگرنه `null`.
- جمع‌های سطح مزرعه (کل اقدام امروز/عقب‌افتاده، مساحت کل) را **فرانت‌اند** از قطعه‌ها جمع می‌زند؛ بک‌اند لازم نیست.

## ۸. دوره‌ی کشت (`crop_seasons`) از روی عملیات کاشت
هیچ صفحه‌ای برای ساخت دوره‌ی کشت وجود ندارد؛ کاربر فقط عملیات «کاشت» ثبت می‌کند و بک‌اند دوره را مدیریت می‌کند:
- `POST /operations` با `operation_type='planting'` و `crop_name`: یک دوره‌ی `planned` بساز (`plot_id`، `crop_name`، `variety`، `start_date = scheduled_date`) و `crop_season_id` عملیات را به آن وصل کن. بدون `crop_name` دوره‌ای ساخته نمی‌شود.
- وقتی عملیات کاشت `completed` شود: دوره `active` و `actual_start_date = completed_date`. اگر دوباره از `completed` برگشت: دوره به `planned` و `actual_start_date = NULL`.
- وقتی عملیات `harvesting` یک قطعه `completed` شود: دوره‌ی فعال آن قطعه `completed` و `actual_end_date = completed_date`. با برگشت وضعیت، به `active` برگردد.
- کاشتِ `cancelled`: دوره‌ی `planned` همراهش `cancelled`. حذف عملیات کاشت: اگر دوره‌اش `planned` بود حذف شود.
- عملیات‌های دیگر قطعه (که `crop_season_id` ندارند) می‌توانند هنگام ساخت به دوره‌ی `active` همان قطعه وصل شوند (اختیاری، برای گزارش‌های آینده).
- اگر `plot_id` یک عملیات عوض شد، `crop_season_id` آن `NULL` شود (برای عملیات کاشت با دوره‌ی `planned`، خود دوره هم به قطعه‌ی جدید منتقل شود).
- قیود دیتابیس دوره‌ی کشت (ترتیب تاریخ‌ها) را رعایت کن.

## ۹. صفحه‌های فرانت‌اند و درخواست‌هایشان
مسیرها مسیرهای فرانت‌اند هستند. همه به‌جز ورود و ثبت‌نام نیاز به نشست معتبر دارند.

| صفحه | محتوا | درخواست‌ها |
|---|---|---|
| `/login`، `/register` | فرم‌ها. ثبت‌نام: نام، موبایل، ایمیل اختیاری، رمز و تکرار | `POST /auth/register`، `POST /auth/login` |
| قاب بعد از ورود | منوی کشویی (موبایل) / نوار کناری (لپ‌تاپ): داشبورد، تقویم، ثبت عملیات، جست‌وجو در سوابق، مزرعه‌ها؛ پایین منو نام کاربر و «خروج» | `GET /auth/me`، `POST /auth/logout` |
| `/dashboard` | «روز بخیر»؛ ۳ کار پیش رو (کارت عملیات)؛ دکمه‌ی «ثبت عملیات جدید» (مودال؛ بعد از ثبت به `/operations/recent` می‌رود)؛ مزرعه‌های من (نام‌ها) و دکمه‌ی افزودن؛ فرم فیلتر سوابق (بازه‌ی تاریخ، مزرعه، قطعه) که به `/operations/search?...` می‌رود | `GET /operations?status=planned,in_progress&order=asc&limit=3`، `GET /farms` |
| `/operations/recent` | دکمه‌ی ثبت عملیات (مودال) و ۵ عملیات آخر | `GET /operations?limit=5&sort=created`، `POST /operations` |
| `/operations/search` | همان فیلترها (از آدرس خوانده و پر می‌شوند: `from,to,farm,plot` و گاهی `status,order`)، برچسب فیلتر وضعیت، نتایج با «نمایش بیشتر» | `GET /farms`، `GET /operations?...&limit=20&offset=N` |
| `/calendar` | تقویم شمسی ماهانه. هر عملیات غیرلغوشده یک نقطه‌ی رنگی در روز مؤثرش (پر = انجام‌شده، توخالی = برنامه‌ریزی‌شده؛ رنگ = نوع). کلیک روی روز، عملیات همان روز را زیر تقویم نشان می‌دهد (از همان داده‌ی ماه؛ درخواست جدا نمی‌زند). دکمه‌ی «افزودن» | `GET /operations/calendar?from&to` (با هر تغییر ماه یا سال، و بعد از هر تغییر عملیات) |
| `/farms` | نام مزرعه‌ها و دکمه‌ی افزودن (مودال: نام، آدرس، توضیحات) | `GET /farms`، `POST /farms` |
| `/farms/{id}` | نام مزرعه؛ «وضعیت کنونی»: دو عدد (جمع `today_count` و جمع `overdue_count` قطعه‌ها)؛ کارت هر قطعه؛ دکمه‌ی افزودن قطعه (مودال)؛ اطلاعات مزرعه و ویرایش (مودال) | `GET /farms/{id}`، `POST /farms/{id}/plots`، `PATCH /farms/{id}` |
| `/plots/{id}` | بازگشت به مزرعه؛ وضعیت کنونی (دو عدد، محصول فعلی، تاریخ کاشت، آخرین آبیاری/کوددهی/سم‌پاشی)؛ ۳ اقدام بعدی + لینک «تمام اقدامات آینده»؛ ۳ عملیات اخیر + لینک «تمام عملیات‌های گذشته»؛ اطلاعات قطعه و ویرایش (مودال) | `GET /plots/{id}`، `PATCH /plots/{id}` |

**معنی رنگ کارت قطعه** (فرانت‌اند از شمارنده‌ها می‌سازد): `overdue_count > 0` قرمز، وگرنه `today_count > 0` زرد، وگرنه سبز.

**کارت و مودال عملیات (در همه‌ی صفحه‌ها یکسان)**
- دایره‌ی وضعیت: خالی = `planned/in_progress`، تیک = `completed`، ضرب‌در = `cancelled`.
- سه‌نقطه: «ویرایش» (مودال)، «انجام شد» (`PATCH {status:"completed"}`، فقط برای عملیات باز)، «لغو» (`PATCH {status:"cancelled"}`، فقط برای عملیات باز)، «حذف» (`DELETE`).
- مودال (افزودن و ویرایش): نوع، عنوان، مزرعه و قطعه، تاریخ و ساعت برنامه‌ریزی، وضعیت (انجام نشده، انجام شده، لغو شده)، تاریخ انجام (فقط وقتی انجام شده)، توضیحات؛ و برای کاشت (فقط افزودن) محصول و رقم. «انجام نشده» در فرانت‌اند یعنی `planned`؛ فرانت‌اند `in_progress` را مثل «انجام نشده» نشان می‌دهد و اگر وضعیت دست نخورد آن را نمی‌فرستد.

## ۱۰. خارج از محدوده‌ی این نسخه
- endpoint یادآوری (`reminders`) و اعلان‌ها؛ «کارهای پیش رو» از خود جدول عملیات می‌آید، نه از `reminders`.
- endpoint مستقل دوره‌ی کشت؛ حذف مزرعه یا قطعه؛ بازیابی رمز؛ تأیید موبایل یا ایمیل؛ نقش‌ها و چندکاربره بودن یک مزرعه؛ ارسال پیامک یا ایمیل.

## ۱۱. کارایی و نگهداری
- ایندکس‌های پیشنهادی: `farms(owner_id)`، `plots(farm_id)`، `operations(plot_id, status, scheduled_date)`، `operations(created_at)`، `auth_sessions(token_hash)` (یکتا).
- شمارنده‌های `GET /farms/{id}` را با چند query تجمیعی بساز (نه یک query برای هر قطعه).
- ورود را محدود به تعداد تلاش کن (مثلاً ۱۰ تلاش در ۱۰ دقیقه) و پیام خطای `login` را برای شماره‌ی ناموجود و رمز اشتباه یکسان نگه دار.
- حداکثر طول‌ها: `full_name` ۱۰۰، `name` مزرعه و قطعه ۱۲۰، `code` ۳۰، `soil_type` ۶۰، `address` ۵۰۰، `title` ۱۲۰، `description` ۲۰۰۰.
- پیکربندی با متغیر محیطی: `SESSION_TTL_HOURS` (پیش‌فرض ۲۴)، مسیر فایل SQLite، مبدأهای مجاز CORS.
- یک اسکریپت seed برای توسعه بنویس (۱ کاربر، ۳ مزرعه، چند قطعه و عملیات با تاریخ‌های نسبت به امروز، شامل عقب‌افتاده و امروز).

## ۱۲. سناریوهای پذیرش (باید همه برقرار باشند)
1. ثبت‌نام با شماره‌ی تکراری `409` می‌دهد؛ ورود با رمز غلط `401`؛ بعد از `logout`، همان توکن `401` می‌دهد.
2. کاربر B با شناسه‌ی مزرعه/قطعه/عملیات کاربر A به `404` می‌خورد.
3. ساخت قطعه با نام یا کد تکراری در یک مزرعه `409`؛ با `area_m2 = 0` یا منفی `422`.
4. ساخت عملیات برای قطعه‌ای که مال کاربر دیگری است ممکن نیست.
5. عملیاتی با `scheduled_date` دیروز و `planned`: در `overdue_count` قطعه و مزرعه می‌آید، در «کارهای پیش رو» اول می‌آید، و `next_operation` همان است. با `PATCH {status:"completed"}` از هر دو شمارنده خارج می‌شود و `completed_date` برابر امروز می‌شود.
6. عملیات ۴ فروردین برنامه‌ریزی‌شده و `PATCH {status:"completed", completed_date:"<۱۰ فروردین>"}`: در `GET /operations/calendar` فقط در ۱۰ فروردین ظاهر می‌شود. بعد از `PATCH {status:"planned"}` به ۴ فروردین برمی‌گردد و `completed_date` برابر `null` می‌شود.
7. عملیات `cancelled` در تقویم برگردانده می‌شود (با تاریخ مؤثر = `scheduled_date`) ولی در `today_count`، `overdue_count` و «کارهای پیش رو» نمی‌آید.
8. ثبت کاشت با `crop_name`، بعد تکمیل آن: `current_season` قطعه `{crop_name, status:"active", actual_start_date}` می‌شود.
9. جست‌وجو با `from`, `to`, `farm`, `plot`, `status` درست فیلتر می‌کند؛ با ۲۵ نتیجه، صفحه‌ی اول دقیقاً ۲۰ آیتم و `offset=20` پنج آیتم می‌دهد.
10. `PATCH /farms/{id}` با فقط یکی از `latitude` و `longitude` `422` می‌دهد؛ با هر دو `null` مختصات پاک می‌شود.
11. تغییر `scheduled_date`، تکمیل، لغو یا حذف عملیات، یادآوری‌های `pending` آن را `cancelled` می‌کند (حذف: پاک می‌شوند).

## ۱۳. فهرست فرض‌هایی که اینجا گرفته شده (در پایان کار برای مالک پروژه گزارش کن)
- ساعت ثبت‌شده برای `completed_date` غیرِامروز ۱۲:۰۰ به وقت مزرعه است.
- «عملیات‌های اخیر» بر اساس زمان ثبت (`created_at`) است، نه تاریخ برنامه‌ریزی.
- `title` اگر نیامد برچسب فارسی نوع می‌شود.
- در تقویم، عملیات لغوشده برگردانده می‌شود ولی فرانت‌اند برایش نقطه نمی‌گذارد.
