# Components

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


