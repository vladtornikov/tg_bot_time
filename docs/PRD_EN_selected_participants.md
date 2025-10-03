
# Product Requirements Document (PRD)
**Product:** Telegram Meeting-Scheduler Bot  
**Version:** MVP — Selected Participants, Google-only  
**Last updated:** 2025-10-03 15:01 (Asia/Bangkok)

## 1) Overview
We no longer assume all chat members participate. Each meeting has an explicit **participant list** (selected by the organizer at `/meet` or via mentions/replies). The bot validates participants, checks **Google Calendar** availability, computes the **time intersection** for the selected users within **working hours 08:00–20:00**, and proposes **five nearest mutually-available slots** for voting. If none are chosen, the bot proposes the **next five**. Users do **not** propose their own times.

## 2) Objectives
- Provide the **earliest five** mutually-available slots, respecting 08:00–20:00 working hours by default.
- Minimize back-and-forth; organizer confirms after voting.
- Reliability: re-check availability before final event creation.

## 3) Assumptions & Constraints
- Calendar providers: Google-only in MVP; provider abstraction for future Yandex.
- Participants: Explicit per meeting; all selected are **required** in MVP.
- Working hours: Default 08:00–20:00 per user tz (configurable later).
- Time zones: Store UTC; render localized per user.
- Privacy: Minimal details in group; DM consent links/reminders.

## 4) Users
- Organizer: starts `/meet`, selects participants, confirms winning slot.
- Participant: grants Google OAuth, votes, must be free for the chosen slot.

## 5) Core Flow
1. Organizer runs `/meet 45m [topic] @u1 @u2 @u3` (or uses inline participant picker).  
2. Bot **validates participants**, snapshots the list, checks OAuth for each.  
3. If missing OAuth → DM `/link_calendar` → state `awaiting_consent` until all connected.  
4. When all connected, bot queries FreeBusy for each participant in the window (e.g., next 10 business days), **clipped to 08:00–20:00** per user tz.  
5. Bot computes the **intersection** (slots ≥ duration), orders by start time, and posts the **first five** candidates with **Vote** buttons.  
6. If none chosen or on **Next 5**, bot posts the **next five**.  
7. On selection/confirm, bot re-checks FreeBusy and **creates the event** on organizer’s Google Calendar with all participants invited.

## 6) Non-Goals (MVP)
Optional attendees, fairness rotation, advanced preferences UI, admin web app, natural-language parsing.

## 7) Functional Requirements
- `/meet <duration> [topic] [@participants…]` — create meeting; snapshot participants.  
- Participant validation; prompt unknown users to register.  
- Google OAuth flow (`/link_calendar`), consent reminders.  
- FreeBusy aggregation **08:00–20:00** per participant tz.  
- Candidate pagination: **5 at a time**; “Next 5” button.  
- Voting + final confirmation; event creation on organizer’s calendar.

## 8) State Machine
`draft` → `awaiting_consent` → `resolving` → `voting` (5-slot batches) → `confirmed` | `failed/canceled`

## 9) Scheduling Algorithm
Per participant: busy intervals from FreeBusy within window, clipped to 08:00–20:00; complement to free; intersect across all participants; generate slots ≥ duration (snap to 5/15/30 min); order by start; page by 5; re-check FreeBusy before create.

## 10) Data Model
- `users`  
- `oauth_tokens` (provider='google')  
- `chats`  
- `chat_memberships`  
- `meetings`  
- `meeting_participants`  
- `votes`

## 11) API / Bot Integration
- OAuth: `GET /oauth/google/start`, `GET /oauth/google/callback`  
- Meetings: `POST /meetings` (with participants), `POST /meetings/{id}/resolve?cursor=…`, `POST /meetings/{id}/confirm`  
- Bot UI: participant picker; Vote/Next 5 keyboards

## 12) Non-Functional
Security (encrypted tokens, least-privilege); Reliability (idempotent handlers, dedupe keys, retries); Performance (≤30 participants over 10-day window, <2s p95); Observability (structured logs/metrics); Privacy (minimal surface in chat).

## 13) Acceptance Criteria
Given selected, validated participants with Google connected, `/meet 30m` yields five mutually-available slots within working hours; “Next 5” yields subsequent five; confirmation creates event with all participants; tokens never logged.
