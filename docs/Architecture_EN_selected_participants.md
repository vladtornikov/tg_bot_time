
# System Architecture — Telegram Meeting-Scheduler Bot (Selected participants, Google-only)
_Last updated: 2025-10-03 15:01 (Asia/Bangkok)_

## 0) Context
Participants are **explicit per meeting**; the bot validates them, computes **intersection** across their Google FreeBusy within **08:00–20:00**, and paginates **five** slots per page for voting.

## 1) Components
1. **Telegram Bot Adapter (Aiogram 3, FastAPI webhook)** — `/meet`, `/link_calendar`, participant picker, Vote/Next 5, consent DMs.  
2. **API Gateway (FastAPI)** — OAuth start/callback; meetings create/resolve/confirm.  
3. **Scheduler Service** — meeting lifecycle, FreeBusy aggregation, intersection, candidate generation, pagination cursor.  
4. **Calendar Provider Layer** — interface + Google provider (get_freebusy/create_event/revoke, token refresh & error normalization).  
5. **Roster Service** — maintains known users & chat memberships; participant validation.  
6. **Persistence** — PostgreSQL + SQLAlchemy + Alembic — `users`, `oauth_tokens`, `chats`, `chat_memberships`, `meetings`, `meeting_participants`, `votes`.  
7. **Jobs/Workers** — consent reminders, retries for transient provider errors.  
8. **Secrets & Config** — encrypted tokens (KMS/libsodium), YAML + `.env` via Pydantic.  
9. **Observability** — JSON logs, Prometheus metrics; alerting.  
10. **Edge Proxy & TLS** — Nginx/Caddy; secure Telegram webhook.

## 2) Data Model (key)
- `meetings(id, chat_id, organizer_id, topic, duration_min, state, chosen_start_utc, chosen_end_utc, created_at)`  
- `meeting_participants(meeting_id, user_id, role='required')`  
- `votes(meeting_id, user_id, slot_start_utc, slot_end_utc, vote)`

## 3) Flow
```
Group → Bot: /meet 45m "Kickoff" @u1 @u2 @u3
Bot: validate & snapshot participants; check OAuth → awaiting_consent if missing
Scheduler.resolve: get_freebusy for each participant, clip to 08:00–20:00 per tz
Intersect free windows ≥ duration; order by start; post first five with Vote/Next 5
On confirm: re-check FreeBusy; create_event on organizer’s Google; invite all; post success; state=confirmed
```

## 4) Scheduling & Pagination
Working hours default 08:00–20:00 per user tz; intersection across participants; candidates snapped to 5/15/30 min; **5 per page** with cursor; race check on confirm.

## 5) API (MVP)
- `GET /oauth/google/start`; `GET /oauth/google/callback`  
- `POST /meetings`; `POST /meetings/{id}/resolve?cursor=…`; `POST /meetings/{id}/confirm`  
- **Errors:** `AUTH_REQUIRED`, `USER_NOT_KNOWN`, `OAUTH_EXPIRED`, `NO_SLOT_FOUND`, `QUOTA_EXCEEDED`, `RACE_CONFLICT`, `RETRY_LATER`.

## 6) Security & Ops
Encrypt tokens; least-privilege scopes; verify Telegram signature; HTTPS; metrics: `time_to_first_batch_seconds`, `candidate_batches_served_total`, `oauth_conversions_total`, `freebusy_latency_ms`; alerts on quotas/errors.
