# Functional Requirements

- `/meet <duration> [topic] [@participants…]` — create meeting; snapshot participants.  
- Participant validation; prompt unknown users to register.  
- Google OAuth flow (`/link_calendar`), consent reminders.  
- FreeBusy aggregation **08:00–20:00** per participant tz.  
- Candidate pagination: **5 at a time**; "Next 5" button.  
- Voting + final confirmation; event creation on organizer's calendar.


