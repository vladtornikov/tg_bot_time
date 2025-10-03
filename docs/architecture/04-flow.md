# Flow

```
Group → Bot: /meet 45m "Kickoff" @u1 @u2 @u3
Bot: validate & snapshot participants; check OAuth → awaiting_consent if missing
Scheduler.resolve: get_freebusy for each participant, clip to 08:00–20:00 per tz
Intersect free windows ≥ duration; order by start; post first five with Vote/Next 5
On confirm: re-check FreeBusy; create_event on organizer's Google; invite all; post success; state=confirmed
```


