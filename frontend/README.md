# Farm Management Frontend

Run the backend and apply its migrations first:

```powershell
.\.venv313\Scripts\alembic.exe upgrade head
.\.venv313\Scripts\uvicorn.exe app.main:app --reload
```

Then run the frontend in a separate terminal:

```powershell
cd frontend
npm ci
npm run dev
```

Open `http://localhost:5173`. Vite proxies `/api` to `http://localhost:8000`, so
the default frontend needs no CORS setting. For a separately hosted API, set
`VITE_API_URL` to its full `/api/v1` URL and allow the frontend origin with the
backend's `CORS_ORIGINS` setting.

Run `python -m app.reminders.worker` in another terminal to publish due in-app
notifications. The frontend now uses the real FastAPI endpoints; mock data is
not used. A reminder entered in the form uses the browser device's local time.

