# Core Flow

1. Organizer runs `/meet 45m [topic] @u1 @u2 @u3` (or uses inline participant picker).  
2. Bot **validates participants**, snapshots the list, checks OAuth for each.  
3. If missing OAuth → DM `/link_calendar` → state `awaiting_consent` until all connected.  
4. When all connected, bot queries FreeBusy for each participant in the window (e.g., next 10 business days), **clipped to 08:00–20:00** per user tz.  
5. Bot computes the **intersection** (slots ≥ duration), orders by start time, and posts the **first five** candidates with **Vote** buttons.  
6. If none chosen or on **Next 5**, bot posts the **next five**.  
7. On selection/confirm, bot re-checks FreeBusy and **creates the event** on organizer's Google Calendar with all participants invited.


