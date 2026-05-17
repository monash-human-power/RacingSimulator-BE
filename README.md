# Racing Simulator Backend

Express + Supabase API for the Racing Simulator frontend.

## Setup

1. Copy `.env.example` to `.env` and fill in Supabase values.
2. Install dependencies:

```bash
npm install
```

3. Apply database schema in Supabase SQL editor:

- `supabase/schema.sql`

4. Install BLE engine dependencies once (Python 3.12+ required):

```bash
npm run engine:install
```

5. Run development servers (Express API + BLE engine together):

```bash
npm run dev
```

This starts the API on port 4000 and the Python BLE engine on port 8000. To run only one service: `npm run dev:api` or `npm run dev:engine`.

## BLE / Trainer Engine (KICKR)

The Python engine service in `engine-service/` handles BLE (FTMS) connections via Bleak and streams live telemetry over WebSocket. Ensure `.env` includes `ENGINE_SERVICE_URL=http://localhost:8000`.

The Express API proxies device operations at `/api/devices/*` to the engine service. The frontend connects to `ws://localhost:8000/ws/engine` for live metrics.

## API Surface

- `POST /api/auth/sign-up`
- `POST /api/auth/sign-in`
- `POST /api/auth/refresh`
- `POST /api/auth/sign-out`
- `POST /api/auth/reset-password`
- `POST /api/auth/update-password`
- `GET /api/auth/me`
- `PATCH /api/auth/profile`
- `GET|POST|PUT|DELETE /api/riders`
- `GET /api/maps`
- `GET|POST|PATCH /api/sessions`
- `GET /api/leaderboard`
- `GET|PUT /api/preferences`
- `GET|POST|PUT /api/race-setups`
- `GET /api/devices/health|state|scan`
- `POST /api/devices/connect|disconnect|control/*`