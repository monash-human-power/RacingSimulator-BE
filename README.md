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

4. Run development server:

```bash
npm run dev
```

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