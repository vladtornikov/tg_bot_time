"""FSM states for bot conversation flows."""
from aiogram.fsm.state import State, StatesGroup


class MeetingCreationStates(StatesGroup):
    """States for meeting creation flow."""
    
    # Initial state
    WAITING_FOR_COMMAND = State()
    
    # Meeting creation flow
    WAITING_FOR_DURATION = State()
    WAITING_FOR_TOPIC = State()
    WAITING_FOR_PARTICIPANTS = State()
    
    # OAuth consent flow
    WAITING_FOR_OAUTH_CONSENT = State()
    
    # Voting flow
    WAITING_FOR_VOTES = State()
    WAITING_FOR_CONFIRMATION = State()
    
    # Final states
    MEETING_CREATED = State()
    MEETING_CONFIRMED = State()
    MEETING_CANCELED = State()


class OAuthStates(StatesGroup):
    """States for OAuth consent flow."""
    
    # Initial state
    WAITING_FOR_OAUTH_START = State()
    
    # OAuth flow
    WAITING_FOR_OAUTH_CODE = State()
    WAITING_FOR_OAUTH_CALLBACK = State()
    
    # Final states
    OAUTH_COMPLETED = State()
    OAUTH_FAILED = State()


class VotingStates(StatesGroup):
    """States for voting flow."""
    
    # Initial state
    WAITING_FOR_VOTES = State()
    
    # Voting flow
    VOTING_IN_PROGRESS = State()
    WAITING_FOR_NEXT_BATCH = State()
    
    # Final states
    VOTING_COMPLETED = State()
    VOTING_CANCELED = State()


class ParticipantSelectionStates(StatesGroup):
    """States for participant selection flow."""
    
    # Initial state
    WAITING_FOR_PARTICIPANTS = State()
    
    # Selection flow
    SELECTING_PARTICIPANTS = State()
    CONFIRMING_PARTICIPANTS = State()
    
    # Final states
    PARTICIPANTS_SELECTED = State()
    PARTICIPANTS_CANCELED = State()
