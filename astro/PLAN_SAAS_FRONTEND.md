# ALTAIR Astro Frontend — SaaS Build-Out Plan

> Status: **planning only** — nothing in this document is implemented yet.
> This supersedes the "coming soon, don't build" note in `astro/README.md`
> and the root `README.md` project-status section once implementation
> actually starts; until then those documents still describe the running
> system accurately, and `templates/` remains the only working UI.

## Goal

Turn `astro/` into the real product frontend: a SaaS-style application with
authenticated accounts, sitting in front of the existing FastAPI fragility
engine. Two account types to start:

1. **Admin / superuser** — manages accounts, sees everything a user sees.
2. **User** — logs in, gets access to the algo (strike list / dashboard views
   backed by `/api/v1/*`), no user-management access.

No billing/plan tiers yet. No changes to the scoring algorithm itself — this
is purely an auth + frontend layer in front of what already exists.

## Why this doesn't exist yet (current state)

- FastAPI (`main.py`) has **no database, no user model, no auth** at all —
  it reads/writes plain CSVs under `data/`. Every `/api/v1/*` route is
  unauthenticated and public.
- `astro/` is a single unauthenticated page (`src/pages/index.astro`) that
  `fetch()`s the backend directly. No routing, no layouts, no session state.
- The dashboard served today at `templates/core/` (Jinja2 + Alpine.js) is
  explicitly single-panel, no-auth, by prior project decision — that decision
  is what's being revisited here, deliberately, at the user's request.

## Architecture decision: auth lives in FastAPI

Add real accounts + auth to the Python backend rather than bolting an
Astro-native auth system in front of a stateless API. Reasoning:
- The backend already owns all business data and is the long-term target for
  the planned Rust/Axum port — adding a second, Node-based source of truth
  for identity would need to be re-ported too, doubling the migration work.
  Keeping identity in the Python/FastAPI layer now means the Rust port later
  only has to re-implement one thing, not reconcile two.
  ("Astro-native auth" was the alternative considered and rejected for this
  reason — noted here so it isn't silently re-proposed later.)
- Astro becomes a normal thin client: it calls `/api/v1/auth/*` and attaches
  the resulting token to every other `/api/v1/*` call. This keeps the API
  usable by other future clients (e.g. the eventual Rust rewrite's own
  frontend, or scripts) without re-deriving auth per-client.

### Backend additions (implementation phase, not now)

- **DB**: SQLite via SQLAlchemy — smallest addition that doesn't disturb the
  existing CSV-based data pipeline (`data/`, `md/` stay exactly as-is; only
  identity/session state is new and lives in its own DB file, e.g.
  `data/altair.db`, gitignored alongside the rest of `data/`).
- **User model**: `id, email, password_hash, role (admin|user), created_at,
  is_active`. Two roles only, no hierarchy beyond that.
- **Auth flow**: password login → JWT (short-lived access token + refresh),
  or server-side session cookie — exact mechanism to be decided at
  implementation time. Either way, `/api/v1/*` routes gain a dependency that
  resolves "current user" and their role.
- **New routes**: `POST /api/v1/auth/register` (admin-only, since there's no
  public signup for a two-role internal tool), `POST /api/v1/auth/login`,
  `POST /api/v1/auth/logout`, `GET /api/v1/auth/me`.
- **Route protection**: existing `/api/v1/strike-list`, `/api/v1/audit`,
  forensic endpoints, archive endpoints all move behind "must be logged in."
  Admin-only: user management endpoints (`GET/POST/PATCH /api/v1/users*`).
- **Seeding**: first admin user needs to be creatable without a UI — a CLI
  command or startup-time env-var-driven bootstrap
  (`ALTAIR_ADMIN_EMAIL`/`ALTAIR_ADMIN_PASSWORD`) so there's always a way in
  on a fresh DB.

## Astro frontend structure (implementation phase, not now)

```
astro/
├── src/
│   ├── layouts/
│   │   ├── AuthLayout.astro       # centered card, no sidebar — login/register
│   │   └── AppLayout.astro        # sidebar + header shell, role-aware nav
│   ├── pages/
│   │   ├── login.astro
│   │   ├── admin/
│   │   │   ├── index.astro         # admin overview
│   │   │   └── users.astro         # user management (list/create/disable)
│   │   ├── dashboard/
│   │   │   └── index.astro         # the algo view — current index.astro content,
│   │   │                             #   gated behind login, moved here
│   │   └── index.astro             # redirects to /login or /dashboard based on session
│   ├── lib/
│   │   ├── api.ts                  # existing fetch client, extended to attach
│   │   │                             #   auth token/cookie to every request
│   │   └── auth.ts                 # session helpers (get current user, role check)
│   └── middleware.ts                # Astro middleware: redirect unauthenticated
│                                      #   requests to /login, redirect non-admins
│                                      #   away from /admin/*
```

Astro's SSR middleware is the enforcement point for route protection
client-side; the FastAPI role checks are the real enforcement (never trust
the frontend redirect alone — every `/api/v1/*` call re-validates the
token/role server-side regardless of which page rendered it).

## Two account types — first-pass scope

| Capability | Admin | User |
|---|---|---|
| Log in | ✅ | ✅ |
| View strike list / dashboard (existing `/api/v1/*` algo data) | ✅ | ✅ |
| Trigger `/api/v1/audit` (re-run scraping/scoring) | ✅ | ✅ (open question — see below) |
| Create/disable user accounts | ✅ | ❌ |
| View all users | ✅ | ❌ |

Open question to resolve before implementation: should a plain `user` be
allowed to trigger a full audit run (it live-scrapes every ticker and takes
several minutes — a shared, expensive, rate-limit-sensitive operation), or
should that stay admin-only with users getting read-only access to
whatever the last completed audit produced? Leaning toward admin-only
trigger + user read-only, but not decided.

## Explicit non-goals (for this phase)

- No subscription/billing tiers, no Stripe, no usage metering.
- No password reset / email verification flows yet (can bootstrap via admin
  directly setting passwords).
- No change to the scoring algorithm, CSV pipeline, or the existing
  `templates/` Jinja2 dashboard — it keeps working as-is throughout, since
  the Astro app is additive until it's ready to replace it.
- No changes yet to `astro/README.md` project-status wording or the root
  `README.md` "project status" section, or `CLAUDE.md`'s "no accounts/auth,
  one-panel" note — those get updated together, in the same change, once
  implementation actually begins (tracked as a to-do, not done speculatively
  ahead of the code).

## Suggested implementation order (when the user says go)

1. Backend: DB + User model + password hashing + login/me endpoints, admin
   bootstrap seeding. Verify with `curl` before touching Astro at all.
2. Backend: role-gate the existing `/api/v1/*` routes.
3. Astro: login page + session/token handling in `lib/auth.ts` +
   middleware-based redirects.
4. Astro: move current `index.astro` dashboard content behind
   `/dashboard`, wire `lib/api.ts` to attach the auth token.
5. Astro: `/admin/users` page (list, create, disable) calling the new
   admin-only endpoints.
6. Update `CLAUDE.md` / `README.md` / `astro/README.md` together to reflect
   the new architecture and retire the "don't build astro" guidance.
