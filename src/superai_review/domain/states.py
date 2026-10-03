from enum import StrEnum


class ReviewState(StrEnum):
    CREATED = "CREATED"
    INGESTING = "INGESTING"
    EXTRACTING = "EXTRACTING"
    PREPARING_CONTEXT = "PREPARING_CONTEXT"
    PROPOSING = "PROPOSING"
    REVIEWING = "REVIEWING"
    DEBATING = "DEBATING"
    SYNTHESIZING = "SYNTHESIZING"
    COMPLETED = "COMPLETED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


TERMINAL_STATES = frozenset(
    {
        ReviewState.COMPLETED,
        ReviewState.PARTIAL,
        ReviewState.FAILED,
        ReviewState.CANCELLED,
    }
)

_ALLOWED_TRANSITIONS: dict[ReviewState, frozenset[ReviewState]] = {
    ReviewState.CREATED: frozenset(
        {ReviewState.INGESTING, ReviewState.FAILED, ReviewState.CANCELLED}
    ),
    ReviewState.INGESTING: frozenset(
        {ReviewState.EXTRACTING, ReviewState.FAILED, ReviewState.CANCELLED}
    ),
    ReviewState.EXTRACTING: frozenset(
        {ReviewState.PREPARING_CONTEXT, ReviewState.FAILED, ReviewState.CANCELLED}
    ),
    ReviewState.PREPARING_CONTEXT: frozenset(
        {ReviewState.PROPOSING, ReviewState.FAILED, ReviewState.CANCELLED}
    ),
    ReviewState.PROPOSING: frozenset(
        {
            ReviewState.REVIEWING,
            ReviewState.PARTIAL,
            ReviewState.FAILED,
            ReviewState.CANCELLED,
        }
    ),
    ReviewState.REVIEWING: frozenset(
        {
            ReviewState.DEBATING,
            ReviewState.SYNTHESIZING,
            ReviewState.PARTIAL,
            ReviewState.FAILED,
            ReviewState.CANCELLED,
        }
    ),
    ReviewState.DEBATING: frozenset(
        {
            ReviewState.SYNTHESIZING,
            ReviewState.PARTIAL,
            ReviewState.FAILED,
            ReviewState.CANCELLED,
        }
    ),
    ReviewState.SYNTHESIZING: frozenset(
        {
            ReviewState.COMPLETED,
            ReviewState.PARTIAL,
            ReviewState.FAILED,
            ReviewState.CANCELLED,
        }
    ),
    ReviewState.COMPLETED: frozenset(),
    ReviewState.PARTIAL: frozenset(),
    ReviewState.FAILED: frozenset(),
    ReviewState.CANCELLED: frozenset(),
}


class InvalidStateTransition(ValueError):
    pass


def can_transition(current: ReviewState, target: ReviewState) -> bool:
    return target in _ALLOWED_TRANSITIONS[current]


def validate_transition(current: ReviewState, target: ReviewState) -> None:
    if not can_transition(current, target):
        raise InvalidStateTransition(f"invalid review state transition: {current} -> {target}")
