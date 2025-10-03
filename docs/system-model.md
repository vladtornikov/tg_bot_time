# System Model — Telegram Meeting-Scheduler Bot

**Version:** MVP — Selected Participants, Google-only  
**Last updated:** 2025-10-03 22:19 (Asia/Bangkok)

## 1. System Overview

The Telegram Meeting-Scheduler Bot is a system that enables explicit participant selection for meetings, validates Google Calendar availability, computes time intersections within working hours (08:00–20:00), and proposes five nearest mutually-available slots for voting. The system emphasizes reliability through re-checking availability before final event creation.

### Core Principles
- **Explicit Participation**: Each meeting has a defined participant list selected by the organizer
- **Time Intersection**: System computes mutual availability across selected participants
- **Working Hours Constraint**: Default 08:00–20:00 per user timezone
- **Batch Voting**: Five slots presented at a time with pagination
- **Reliability**: Re-validate availability before creating final events

## 2. Entity Model

### 2.1 Core Entities

#### User
- **Purpose**: Represents a Telegram user who can participate in meetings
- **Attributes**:
  - `id`: Unique identifier
  - `telegram_id`: Telegram user ID
  - `username`: Telegram username (optional)
  - `first_name`: User's first name
  - `last_name`: User's last name (optional)
  - `timezone`: User's timezone (default UTC)
  - `working_hours_start`: Start of working hours (default 08:00)
  - `working_hours_end`: End of working hours (default 20:00)
  - `created_at`: Account creation timestamp
  - `updated_at`: Last update timestamp

#### Chat
- **Purpose**: Represents a Telegram chat/group where meetings can be scheduled
- **Attributes**:
  - `id`: Unique identifier
  - `telegram_chat_id`: Telegram chat ID
  - `title`: Chat title
  - `type`: Chat type (group, supergroup, channel)
  - `created_at`: Chat registration timestamp

#### ChatMembership
- **Purpose**: Represents user membership in a chat
- **Attributes**:
  - `id`: Unique identifier
  - `chat_id`: Reference to Chat
  - `user_id`: Reference to User
  - `role`: Membership role (member, admin, etc.)
  - `joined_at`: When user joined the chat

#### OAuthToken
- **Purpose**: Stores encrypted OAuth tokens for calendar providers
- **Attributes**:
  - `id`: Unique identifier
  - `user_id`: Reference to User
  - `provider`: Calendar provider (google)
  - `access_token`: Encrypted access token
  - `refresh_token`: Encrypted refresh token
  - `expires_at`: Token expiration timestamp
  - `scope`: OAuth scopes granted
  - `created_at`: Token creation timestamp
  - `updated_at`: Last token refresh timestamp

#### Meeting
- **Purpose**: Represents a scheduled meeting with its lifecycle state
- **Attributes**:
  - `id`: Unique identifier
  - `chat_id`: Reference to Chat where meeting was created
  - `organizer_id`: Reference to User who created the meeting
  - `topic`: Meeting topic/description
  - `duration_min`: Meeting duration in minutes
  - `state`: Current meeting state (draft, awaiting_consent, resolving, voting, confirmed, failed, canceled)
  - `chosen_start_utc`: Selected meeting start time (UTC)
  - `chosen_end_utc`: Selected meeting end time (UTC)
  - `created_at`: Meeting creation timestamp
  - `updated_at`: Last state change timestamp

#### MeetingParticipant
- **Purpose**: Represents a user's participation in a specific meeting
- **Attributes**:
  - `id`: Unique identifier
  - `meeting_id`: Reference to Meeting
  - `user_id`: Reference to User
  - `role`: Participation role (required, optional)
  - `added_at`: When participant was added

#### Vote
- **Purpose**: Represents a user's vote for a specific time slot
- **Attributes**:
  - `id`: Unique identifier
  - `meeting_id`: Reference to Meeting
  - `user_id`: Reference to User
  - `slot_start_utc`: Start time of voted slot (UTC)
  - `slot_end_utc`: End time of voted slot (UTC)
  - `vote`: Vote value (yes, no, maybe)
  - `voted_at`: When vote was cast

### 2.2 Entity Relationships

```
User (1) ←→ (N) ChatMembership (N) ←→ (1) Chat
User (1) ←→ (N) OAuthToken
User (1) ←→ (N) Meeting (as organizer)
User (N) ←→ (N) MeetingParticipant (N) ←→ (1) Meeting
User (N) ←→ (N) Vote (N) ←→ (1) Meeting
Meeting (1) ←→ (N) MeetingParticipant
Meeting (1) ←→ (N) Vote
```

## 3. Process Model

### 3.1 Meeting Creation Process

#### Process: Create Meeting
**Trigger**: Organizer sends `/meet <duration> [topic] [@participants...]` command

**Steps**:
1. **Validate Command**: Parse duration, topic, and participant mentions
2. **Validate Participants**: Check if mentioned users exist in the system
3. **Snapshot Participants**: Create MeetingParticipant records for all mentioned users
4. **Check OAuth Status**: Verify all participants have valid Google OAuth tokens
5. **Set State**: 
   - If all participants have OAuth → `resolving`
   - If any participant missing OAuth → `awaiting_consent`
6. **Create Meeting Record**: Save meeting with initial state

**Outputs**:
- Meeting record created
- MeetingParticipant records created
- State set to `awaiting_consent` or `resolving`

#### Process: Handle Missing OAuth
**Trigger**: Meeting state is `awaiting_consent`

**Steps**:
1. **Identify Missing OAuth**: Find participants without valid Google OAuth tokens
2. **Send DM Requests**: Send `/link_calendar` command to each participant via DM
3. **Monitor OAuth Completion**: Wait for all participants to complete OAuth flow
4. **Transition State**: When all OAuth complete → `resolving`

**Outputs**:
- DM messages sent to participants
- State transition to `resolving` when complete

### 3.2 Time Slot Resolution Process

#### Process: Resolve Available Slots
**Trigger**: Meeting state is `resolving`

**Steps**:
1. **Query FreeBusy**: For each participant, query Google Calendar FreeBusy API
2. **Apply Working Hours**: Clip results to 08:00–20:00 per participant timezone
3. **Compute Intersection**: Find common free time slots across all participants
4. **Generate Candidates**: Create time slots ≥ meeting duration, snapped to 5/15/30 minutes
5. **Order by Start Time**: Sort candidates chronologically
6. **Paginate Results**: Prepare first batch of 5 candidates
7. **Transition State**: Set state to `voting`
8. **Post Candidates**: Display first 5 candidates with Vote buttons

**Outputs**:
- Time slot candidates generated
- First 5 candidates posted with voting interface
- State set to `voting`

#### Process: Handle Voting
**Trigger**: Users vote on time slot candidates

**Steps**:
1. **Record Votes**: Save user votes in Vote table
2. **Monitor Voting Progress**: Track voting completion
3. **Handle "Next 5"**: If requested, generate next batch of 5 candidates
4. **Handle Selection**: When a slot is selected, validate choice
5. **Transition State**: Set state to `confirmed` or continue `voting`

**Outputs**:
- Vote records created
- Next batch of candidates (if requested)
- State transition to `confirmed` when slot selected

### 3.3 Event Creation Process

#### Process: Create Calendar Event
**Trigger**: Meeting state is `confirmed`

**Steps**:
1. **Re-validate Availability**: Re-check FreeBusy for all participants
2. **Verify Slot Still Available**: Ensure selected slot is still free
3. **Create Event**: Create Google Calendar event on organizer's calendar
4. **Invite Participants**: Add all participants as event attendees
5. **Send Confirmations**: Notify all participants of confirmed meeting
6. **Update Meeting**: Set chosen_start_utc and chosen_end_utc
7. **Final State**: Set state to `confirmed`

**Outputs**:
- Google Calendar event created
- Participant notifications sent
- Meeting record updated with final times

## 4. State Machine Model

### 4.1 Meeting States

```
draft → awaiting_consent → resolving → voting → confirmed
  ↓           ↓              ↓          ↓
failed ← canceled ← failed ← failed ← failed
```

#### State Definitions

**draft**: Initial state when meeting is created
- **Transitions**: → `awaiting_consent` (if OAuth missing) or → `resolving` (if all OAuth present)

**awaiting_consent**: Waiting for participants to complete OAuth
- **Transitions**: → `resolving` (when all OAuth complete) or → `failed` (timeout/error)

**resolving**: Computing available time slots
- **Transitions**: → `voting` (slots found) or → `failed` (no slots found)

**voting**: Users voting on time slot candidates
- **Transitions**: → `confirmed` (slot selected) or → `voting` (next batch) or → `failed` (error)

**confirmed**: Meeting scheduled and calendar event created
- **Transitions**: Terminal state

**failed**: Meeting creation failed
- **Transitions**: Terminal state

**canceled**: Meeting canceled by organizer
- **Transitions**: Terminal state

### 4.2 State Transition Rules

1. **OAuth Validation**: All participants must have valid Google OAuth tokens
2. **Time Window**: Search window limited to next 10 business days
3. **Working Hours**: All slots must fall within 08:00–20:00 per participant timezone
4. **Minimum Duration**: Generated slots must be ≥ meeting duration
5. **Pagination**: Maximum 5 candidates per voting batch
6. **Re-validation**: Availability re-checked before final event creation

## 5. Constraint Model

### 5.1 Business Constraints

#### Participant Constraints
- **Required Participants**: All selected participants are required (no optional attendees in MVP)
- **Maximum Participants**: ≤30 participants per meeting
- **OAuth Requirement**: All participants must have Google Calendar access

#### Time Constraints
- **Working Hours**: Default 08:00–20:00 per user timezone
- **Time Window**: Search limited to next 10 business days
- **Duration Snapping**: Slots snapped to 5/15/30 minute intervals
- **Timezone Handling**: Store UTC, render localized per user

#### Voting Constraints
- **Batch Size**: Exactly 5 candidates per voting batch
- **Pagination**: "Next 5" button for additional candidates
- **Vote Types**: Yes/No/Maybe voting options
- **Selection Rule**: First slot to receive sufficient votes is selected

### 5.2 Technical Constraints

#### Performance Constraints
- **Response Time**: ≤2 seconds p95 for slot resolution
- **Participant Limit**: ≤30 participants over 10-day window
- **Concurrent Meetings**: System must handle multiple concurrent meeting creations

#### Security Constraints
- **Token Encryption**: All OAuth tokens encrypted at rest
- **Least Privilege**: Minimal OAuth scopes requested
- **Telegram Verification**: All webhook requests verified via Telegram signature
- **HTTPS Only**: All external communications over HTTPS

#### Reliability Constraints
- **Idempotent Operations**: All handlers must be idempotent
- **Retry Logic**: Transient provider errors must be retried
- **Deduplication**: Prevent duplicate meeting creation
- **Race Condition Handling**: Re-check availability before event creation

### 5.3 Data Constraints

#### Data Integrity
- **Foreign Key Constraints**: All references must be valid
- **Unique Constraints**: Prevent duplicate votes per user per slot
- **Cascade Rules**: Define deletion behavior for related records

#### Data Privacy
- **Minimal Exposure**: Minimal meeting details in group chat
- **DM Consent**: OAuth consent requests sent via DM only
- **Token Security**: OAuth tokens never logged or exposed

## 6. Interface Model

### 6.1 External Interfaces

#### Telegram Bot Interface
- **Commands**: `/meet`, `/link_calendar`
- **Interactive Elements**: Participant picker, Vote buttons, "Next 5" button
- **Messages**: Status updates, error messages, confirmations

#### Google Calendar API Interface
- **OAuth Flow**: Authorization and token refresh
- **FreeBusy API**: Query participant availability
- **Calendar API**: Create events and invite attendees

#### REST API Interface
- **OAuth Endpoints**: `/oauth/google/start`, `/oauth/google/callback`
- **Meeting Endpoints**: `/meetings`, `/meetings/{id}/resolve`, `/meetings/{id}/confirm`
- **Error Handling**: Standardized error responses

### 6.2 Internal Interfaces

#### Service Interfaces
- **Scheduler Service**: Meeting lifecycle management
- **Calendar Provider Layer**: Abstracted calendar operations
- **Roster Service**: User and chat membership management
- **Persistence Layer**: Database operations

#### Data Flow Interfaces
- **Event Bus**: Inter-service communication
- **Job Queue**: Background task processing
- **Metrics Interface**: Observability data collection

## 7. Quality Attributes

### 7.1 Performance
- **Response Time**: ≤2 seconds p95 for slot resolution
- **Throughput**: Support multiple concurrent meeting creations
- **Scalability**: Handle increasing participant counts

### 7.2 Reliability
- **Availability**: 99.9% uptime target
- **Fault Tolerance**: Graceful handling of provider errors
- **Data Consistency**: ACID compliance for critical operations

### 7.3 Security
- **Authentication**: OAuth 2.0 for calendar access
- **Authorization**: Role-based access control
- **Data Protection**: Encryption at rest and in transit

### 7.4 Usability
- **Ease of Use**: Simple command interface
- **Feedback**: Clear status updates and error messages
- **Accessibility**: Support for various user interfaces

### 7.5 Maintainability
- **Modularity**: Clear separation of concerns
- **Testability**: Comprehensive test coverage
- **Documentation**: Clear system documentation

## 8. Risk Model

### 8.1 Technical Risks
- **API Rate Limits**: Google Calendar API quotas
- **Token Expiration**: OAuth token refresh failures
- **Network Issues**: Connectivity problems with external services

### 8.2 Business Risks
- **User Adoption**: Low participation rates
- **Privacy Concerns**: Calendar data exposure
- **Scalability Limits**: Performance degradation with growth

### 8.3 Mitigation Strategies
- **Rate Limiting**: Implement request throttling
- **Token Management**: Proactive token refresh
- **Fallback Mechanisms**: Graceful degradation
- **Monitoring**: Comprehensive observability
- **Testing**: Extensive test coverage

## 9. Evolution Model

### 9.1 MVP Scope
- Google Calendar only
- Required participants only
- Basic voting interface
- Simple time slot resolution

### 9.2 Future Enhancements
- **Additional Providers**: Yandex Calendar support
- **Optional Attendees**: Support for optional participants
- **Advanced Preferences**: User preference management
- **Web Interface**: Admin web application
- **Natural Language**: NLP for meeting creation

### 9.3 Migration Strategy
- **Backward Compatibility**: Maintain API compatibility
- **Gradual Rollout**: Feature flags for new functionality
- **Data Migration**: Schema evolution support
- **User Training**: Documentation and onboarding

This system model provides a comprehensive foundation for understanding, implementing, and evolving the Telegram Meeting-Scheduler Bot system.


