# Phase 0 — Foundations: Plan

Status: **draft, awaiting owner approval** (per SPEC §15). No application code has been written yet.

Goal: by the end of this phase, the Phase 0 acceptance criteria in SPEC §13 are met. That means a deployable, CI-checked Next.js shell with the database, cache and admin auth wired up, plus a replay harness that plays a recorded race from fixtures through a local mock of OpenF1.

---

## 0. Blocking questions (please answer before I start)

1. **Where does the app live?** This repo (`mobilite/helloworld`) currently holds **CardLedger**, an unrelated Pokémon card project, and SPEC §11.1 expects `/app`, `/lib`, `/db` and so on at the repo root. Options:
   - **(a) New repo, e.g. `lawson-watch` (recommended).** Cleanest, and keeps Vercel, CI and Dependabot simple. You'd create the empty repo and add it to this session. I can't create repositories from here.
   - **(b) Subfolder `lawson-watch/` in this repo.** This works, but Vercel gets a "Root Directory" setting and CI needs `working-directory`, which goes against SPEC §11.1's layout.
   - **(c) Replace CardLedger at the root** (move it to a branch or archive). I won't do this without an explicit yes.
2. **Network access for this build session.** This cloud session can't currently reach `api.openf1.org`, `api.jolpi.ca` or `vercel.com`. I need `api.openf1.org` and `api.jolpi.ca` (exact hosts) to record fixtures and to check current API docs, as SPEC §15 requires. Until then, fixture recording is blocked (see §6).
3. **Licence:** OK with MIT for the code (SPEC §11.2 default)?

The owner decisions in SPEC §14 (OpenF1 sponsor tier, Vercel Pro, X budget, name) **don't** block Phase 0. Everything here runs replay-only and degrades cleanly without them.

---

## 1. Scaffold

- `pnpm create next-app` with App Router, TypeScript (`strict: true`, plus `noUncheckedIndexedAccess`), ESLint, Tailwind and the `src`-less layout to match §11.1.
- Prettier, `eslint-config-prettier`, and `pnpm` pinned through `packageManager` in `package.json`. `.nvmrc` set to Node 22.
- shadcn/ui initialised, with only the primitives we need for now: Button, Card, Badge and Sheet.
- Directory skeleton exactly as SPEC §11.1. Empty modules get typed stubs that throw `NotImplemented`, so nothing is silently half-built.
- Route stubs:
  - `/`
  - `/live`
  - `/replay/[sessionKey]`
  - `/stories` (placeholder: "Coming in Phase 2")
  - `/about` with the full §12 disclaimer text
  - `/admin`

## 2. Config & env

- `.env.example` with every variable from SPEC §10, each commented.
- `lib/env.ts` parses `process.env` with Zod into a typed config. Only `DATABASE_URL`, `UPSTASH_REDIS_REST_URL`/`TOKEN` and `CRON_SECRET` are required. Every other integration is exposed as `config.openf1.live: boolean`, `config.x.enabled`, and so on, so features check one flag rather than poking env vars.
- Replay-only boot test: the app builds and serves with only the required vars set.

## 3. Database (Neon + Drizzle)

- `db/schema.ts` holds **all** tables from SPEC §8 now, so later phases add columns rather than reshaping. Details:
  - FK indexes and indexes on queried timestamps.
  - `items.canonical_url` is unique.
  - `items.embedding` is `vector(N)`. N gets pinned when the embedding model is chosen in Phase 2, so the column ships as nullable and a Phase 2 migration fixes the dimension. I'll flag this in the Phase 2 plan.
  - **No body/content column on `items`.** A schema test asserts this, which gets ahead of a Phase 2 criterion.
  - Phase 3 guard prepared now: a CHECK/trigger so a `claims.current_label = 'verified_by_data'` row must have at least one `claim_evidence` row. If a trigger proves awkward under Drizzle, I'll use a deferred constraint trigger written as raw SQL in a migration.
- First migration enables `pgvector`.
- `drizzle-kit generate` produces SQL migrations that are committed. `pnpm db:migrate` runs them, and CI/deploy calls it. They never run on cold start (§11.3).
- `lib/db.ts` uses the `@neondatabase/serverless` driver.
- Local dev and tests use Postgres 16 + pgvector in Docker (`docker-compose.yml`), so CI doesn't need a Neon branch. Neon preview branches per PR can come later.

## 4. Redis (Upstash)

- `lib/redis.ts` uses `@upstash/redis`. Helpers: `getJSON`/`setJSON` with TTL, and `withLock(key, ttl, fn)` (SET NX PX), which the token refresh in Phase 1 needs.
- Test double: an in-memory implementation behind the same interface, so unit tests don't need Upstash.

## 5. Admin auth

- Auth.js v5 with the GitHub provider. The `signIn` callback allows only logins in `ADMIN_GITHUB_LOGINS`, compared case-insensitively. GitHub login is used, never email.
- `middleware.ts` gates `/admin/**`. Everyone else gets 404, not 403, to avoid advertising the route.
- With the auth vars absent, `/admin` shows "Admin not configured" and the public site is unaffected.
- `lib/jobs/auth.ts` provides `requireCronSecret(req)` for `/api/jobs/*`, using a constant-time compare.
- Tests cover an allowlisted login, a non-allowlisted login, a missing config, and a bad cron secret.

## 6. Replay harness (the main Phase 0 deliverable)

- **Recorder** (`scripts/record-session.ts`): given a `session_key`, it pulls every endpoint listed in SPEC §5.1 from OpenF1's free historical API, politely and within its rate limits. Responses are saved as `tests/fixtures/openf1/<session_key>/<endpoint>.json` with a `manifest.json` that records the fetch time, the source URL and the record counts.
  - `location` is large (car positions at about 3.7 Hz). I'll record **only Lawson's car**, plus a single lap of one car for the track outline, and gzip it. If fixtures still exceed a few MB, I'll use Git LFS or a down-sampled copy for tests. I'll report the actual sizes.
  - Default fixture: a full 2026 race that Lawson started. I'll pick one with pit-stop position changes, which is useful for Phase 1 acceptance testing.
- **Mock server** (`tests/mock-openf1/`): a small Node HTTP server (also usable as MSW handlers in Vitest) that serves the fixtures and honours OpenF1's query filters that we use: `session_key`, `driver_number`, and `date>`/`date<`.
  - It has a **virtual clock**: started with `--speed 10 --from <lap|iso>`, it only returns records with `date <= now_virtual`. This lets the same code path behave as if live.
- `lib/sources/openf1.ts` gets its typed interface and Zod schemas now, with an implementation that has a configurable base URL. The mock base URL is used in dev/test and the real one in prod. Phase 1 builds the snapshot on top of this.
- Acceptance: `pnpm replay:mock` starts the mock server. A Vitest integration test walks the virtual clock through the whole race and checks that every endpoint returns monotonic, filter-respecting data.

## 7. Design shell

- Mobile-first layout with:
  - a header showing `APP_NAME`
  - a footer carrying the §12 disclaimer and a "Report an issue" link
  - a dark theme by default, for the 1–4am viewing
  - a neutral palette with no F1 or team marks
- Original simple wordmark and icon (text + generic SVG). The team colour will only ever come from data as a hex value.
- Shared `FreshnessBadge` component, built now because §2.5 "fail visible" runs throughout. It's green, amber or red with plain-English copy.
- Times are rendered with `Intl.DateTimeFormat` in the viewer's zone, falling back to `Pacific/Auckland`. Copy is in NZ English.

## 8. Logging, budget skeleton

- `lib/log.ts`: pino, structured JSON, with a request ID.
- `lib/budget.ts`: interface and Redis counters only (`charge(service, units, usd)` and `isOverCap(service)`), with unit tests. It gets wired to real services in Phase 2.

## 9. CI / repo hygiene

- `.github/workflows/ci.yml`, run on PRs and on `main`:
  - `pnpm install --frozen-lockfile`
  - typecheck
  - lint
  - Vitest, with a Postgres+pgvector service container and migrations applied
  - `next build`
- `.github/workflows/e2e.yml`: Playwright smoke tests (home renders, disclaimer present, `/admin` gated) against the Vercel preview URL, triggered by the `deployment_status` event. This only works once Vercel is connected, so until then it runs against a local `next start`.
- `.github/dependabot.yml` for npm and GitHub Actions, weekly.
- README covering setup, env vars, running replay locally, adding a source, cost notes, and the "data isn't ours" licence note. MIT `LICENSE`, pending your answer to Q3.
- `vercel.json`: functions region `syd1`. The cron block will be included **only as comments/plan** until you decide between Pro and Hobby. A sub-daily cron on Hobby would fail the deploy.

## 10. What you need to do (I can't do these from here)

| Step | Why |
|---|---|
| Create the repo (if option 1a) and add it to this session | §0 Q1 |
| Allow `api.openf1.org`, `api.jolpi.ca` in this session's network | Fixtures + doc checks |
| Vercel: import the repo, add the Neon and Upstash Marketplace integrations (Sydney region), and set `CRON_SECRET` and `AUTH_*` | Deploy, DB, cache, admin login |
| GitHub OAuth app (callback `https://<domain>/api/auth/callback/github`) | Admin login |
| Branch protection on `main` | §11.2 |

## 11. Out of scope for Phase 0

- Any `LawsonSnapshot` computation or Race Live UI (Phase 1).
- Any ingestion or LLM calls.
- Real-time OpenF1 auth: the interface is stubbed, but there's no token call until there's a subscription.

## 12. Risks / notes

- **OpenF1 terms change often.** I couldn't verify current pricing or auth from this session because the network was blocked. A web search suggests real-time access needs the paid sponsor tier and a token from `POST /token`, but I'll re-check the official docs before writing any live code (Phase 1).
- **Vercel cron limits by plan:** unverified for the same reason. I'll re-check before writing `vercel.json` crons.
- **Fixture size and licensing:** these are recorded third-party data committed to the repo. If the repo is public, I'd keep fixtures minimal (one race) and note their source in the README.

## Estimated output

About 1 PR (or 3 small ones: scaffold+CI, DB+auth, replay harness). PRs target `main` from feature branches.
