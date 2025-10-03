# API (MVP)

- `GET /oauth/google/start`; `GET /oauth/google/callback`  
- `POST /meetings`; `POST /meetings/{id}/resolve?cursor=…`; `POST /meetings/{id}/confirm`  
- **Errors:** `AUTH_REQUIRED`, `USER_NOT_KNOWN`, `OAUTH_EXPIRED`, `NO_SLOT_FOUND`, `QUOTA_EXCEEDED`, `RACE_CONFLICT`, `RETRY_LATER`.


