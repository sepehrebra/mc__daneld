# Farm Management Frontend

Start Django with a separate development database as described in
[the Django setup guide](../django_backend/README.md). Then start Vite from
the repository root in another terminal:

```powershell
cd frontend
npm ci
npm run dev
```

Open `http://localhost:5173`. Vite proxies `/api` to `http://127.0.0.1:8000`, so
the default frontend needs no CORS setting. For a separately hosted API, set
`VITE_API_URL` to its full `/api/v1` URL and allow the frontend origin with the
backend's `CORS_ORIGINS` setting.

The frontend uses the live API by default. With Django running on the seeded
development database and `DJANGO_DEMO_PASSWORD` set to the seed password, run
`node scripts/smoke-django.mjs` from `frontend` to exercise the actual frontend
API client through a local Vite proxy. Run `npm run build` to verify the bundle.

The calendar screen is a placeholder. Calendar responses are covered by the
Django acceptance tests. Notification and reminder screens are outside the
Django API contract.

