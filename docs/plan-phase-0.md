# Phase 0 — Foundations: Plan (revised)

Status: **draft, awaiting owner approval** (per SPEC §15). No application code has been written yet.

## Scope change (owner direction, 2026-11-08)

The app no longer shows live race position or timing. **Race Live is removed.** Its replacement is **Race Chat**: a live feed of what people are saying on social media about Liam Lawson while a session is on.

What this changes from SPEC v1:

| SPEC v1 | Revised |
|---|---|
| Race Live: position, gaps, tyres, pits, track map (§5) | **Removed.** No `LawsonSnapshot`, no live OpenF1 subscription, no track map |
| Social posts were one input to the Story Feed, X disabled by default | **Social chat during sessions is the main feature** |
| OpenF1 paid subscription (§14.1) | Not needed. A free schedule source is only used to know *when* a session is on |
| Replay harness of OpenF1 timing data | Replay harness of **social posts** on a virtual race clock |

Still to confirm (see §0): whether the Story Feed and Claims Check stay.

---

## 0. Questions for the owner

1. **Which repo should this go in?** This is unchanged from the first draft. My recommendation is a new repo, e.g. `lawson-watch`, because this one holds CardLedger.
2. **Do the Story Feed (news) and Claims Check stay?**
   - If Claims Check stays, it still needs free *historical* results data (Jolpica/OpenF1) to check result claims after a race. This is not live timing.
   - If both are dropped, the app becomes Race Chat only.
3. **Which social sources?** Live keyword search is only possible on some platforms (see §1). X is the obvious one, but it is pay-per-use and is the main running cost.
4. **Abuse filtering:** OK to hide abusive or hateful posts by default (see §2)?
5. **Licence:** MIT for the code?

---

## 1. Sources for Race Chat

Each option below needs its current terms and pricing checked against the platform's docs before I use it. This session's network blocks those sites, so none of this is verified yet.

| Source | Live keyword search? | Cost | Notes |
|---|---|---|---|
| **X API** (recent search) | Yes | Pay-per-use, likely the largest cost on race day | Volume spikes during races. Needs a hard daily cap (SPEC §9). Posts are displayed via official embed or under X's display rules |
| **Bluesky** (AT Protocol: `searchPosts`, or Jetstream firehose) | Yes | Free, open API | A good free primary or secondary source. Has a growing F1 community |
| **Reddit** (r/formula1 race-day threads) | Thread polling | API terms and pricing for this use need checking | Race threads are where much F1 chat happens. Comments mentioning Lawson can be filtered from them |
| **YouTube** live chat on watch-along streams | Per-stream only | Uses Data API quota | Optional. Needs a curated channel list |
| Instagram / TikTok | No official keyword search | — | Still out of scope. Only curated official-account embeds |

Proposed v1: **Bluesky + X (capped)**, with Reddit if the terms allow it.

## 2. Race Chat behaviour (Phase 1 replacement, outlined here for context)

- **Session-aware.** A free schedule source (Jolpica, OpenF1 `sessions`) tells the app when a session is live. Polling runs at a race-day pace from about 30 min before the start to 1h after the finish. Between races it runs slowly or not at all.
- **Driver-keyed.** The search terms come from `DRIVER_FULL_NAME`, `DRIVER_ACRONYM` and a configurable hashtag list. No team is hardcoded.
- **Relevance filter.** Rules first: the post mentions Lawson plus F1 context. A cheap LLM pass then handles ambiguous posts and other people called Liam Lawson. It runs in batches and is capped by budget.
- **Abuse and safety filter (on by default).** Lawson has drawn heavy online abuse. Without filtering, a feed of raw posts would amplify it. Posts classified as abusive, hateful or harassing are hidden, as are slurs, and so are posts aimed at his family or partner (in line with SPEC's personal-life exclusion). The filter is conservative: when unsure, it hides.
- **Feed UI.** A single scrolling column of posts, newest first, with an "N new posts" pill rather than a jumping list. Filters: All / Top (engagement) / Verified & official accounts.
- **Moments.** Spikes in post volume are detected and labelled with the race time ("Big spike at 14:32 — 3× normal"). Post counts are the signal, not timing data.
- **Fail visible.** The badge shows each source's status ("X paused — daily budget reached", "Bluesky live").
- **After the race** the chat is archived per session and replayable.

## 3. Scaffold, config, DB, Redis, auth, CI

These parts are unchanged from the first draft:

- Next.js App Router, strict TypeScript, Tailwind + shadcn/ui
- Zod-validated env
- Drizzle + Neon (pgvector)
- Upstash Redis with lock helper
- Auth.js GitHub allowlist for `/admin`
- `requireCronSecret`
- pino logging
- `lib/budget.ts`
- CI (typecheck, lint, Vitest with Postgres service, build)
- Playwright smoke tests
- Dependabot, README, `.env.example`

Route and schema changes:

- **Routes:** `/` (next session countdown, or the live chat when a session is on), `/chat/[sessionKey]` (live or archived), `/about`, `/admin`. `/live` and `/replay` are removed.
- **New tables:**
  - `social_posts`: id, platform, platform_post_id **unique**, author_handle, author_is_official, posted_at, fetched_at, url, session_key, relevance, abuse_flag, hidden, engagement_json. Post text is only stored where the platform's terms allow it. For X, store IDs and render via embed.
  - `chat_sessions`: session_key, start/end, status, post counts.
  - `chat_moments`: session_key, at, post_rate, label.
- **Unchanged tables:** `sources`, `audit_log` and `budget_usage`. Story and claim tables stay only if you keep those features (Q2).
- **Env:**
  - Add `BLUESKY_*`, `REDDIT_*`, `DRIVER_HASHTAGS`, and `HIDE_ABUSE=true`.
  - Drop `OPENF1_USERNAME/PASSWORD`.
  - X becomes `X_ENABLED` plus a cap. It may still default to false until you set a budget.

## 4. Replay harness (revised)

- The harness uses **synthetic fixtures**: realistic generated posts on a race timeline (start, incidents, pit window, finish), with spikes. They are not copies of real users' posts. This avoids committing third-party users' content to the repo (a platform-terms and privacy issue, especially for a public repo).
- It also includes **real recorded API responses with the text stripped or replaced**, so each adapter's Zod schemas are tested against real response shapes.
- A mock server serves the X / Bluesky / Reddit search endpoints on a **virtual clock** (`--speed 10`). The full ingest → filter → feed path then runs as if live.
- Acceptance: a full simulated race plays through the chat UI locally. The abuse-filter test fixtures confirm flagged posts never render.

## 5. What you need to do

| Step | Why |
|---|---|
| Answer §0 | Scope and sources |
| Create the repo and add it to this session | §0 Q1 |
| Allow the source hosts in this session's network (e.g. `api.x.com`, `public.api.bsky.app`, `oauth.reddit.com`, `api.jolpi.ca`) | Check current docs; record response shapes |
| Vercel + Neon + Upstash, GitHub OAuth app, protect `main` | Deploy, DB, cache, admin |
| Set an X budget when you're ready | X is off until then |

## 6. Risks

- **Cost:** chat volume peaks exactly when we poll most. The X cap will cut out mid-race if it is set too low. I'll make it show plainly when that happens, and lean on Bluesky so the feed keeps going.
- **Platform terms:** display, storage and "aggregation" rules differ by platform and change often. I'll check each before building its adapter.
- **Abuse amplification:** this is a reputational and ethical risk. That's why filtering is on by default and there is a human-review path in `/admin`.
- **Unverified so far:** no platform docs could be reached from this session. Everything in §1 is to be confirmed.
