# Data Model (key)

- `meetings(id, chat_id, organizer_id, topic, duration_min, state, chosen_start_utc, chosen_end_utc, created_at)`  
- `meeting_participants(meeting_id, user_id, role='required')`  
- `votes(meeting_id, user_id, slot_start_utc, slot_end_utc, vote)`


