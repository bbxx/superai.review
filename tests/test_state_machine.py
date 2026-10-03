import pytest

from superai_review.domain.states import (
    InvalidStateTransition,
    ReviewState,
    can_transition,
    validate_transition,
)


def test_happy_path_accepts_canonical_transitions() -> None:
    path = [
        ReviewState.CREATED,
        ReviewState.INGESTING,
        ReviewState.EXTRACTING,
        ReviewState.PREPARING_CONTEXT,
        ReviewState.PROPOSING,
        ReviewState.REVIEWING,
        ReviewState.DEBATING,
        ReviewState.SYNTHESIZING,
        ReviewState.COMPLETED,
    ]
    for current, target in zip(path, path[1:]):
        validate_transition(current, target)


def test_review_may_skip_debate() -> None:
    assert can_transition(ReviewState.REVIEWING, ReviewState.SYNTHESIZING)


def test_invalid_jump_is_rejected() -> None:
    with pytest.raises(InvalidStateTransition):
        validate_transition(ReviewState.CREATED, ReviewState.PROPOSING)


@pytest.mark.parametrize(
    "terminal",
    [
        ReviewState.COMPLETED,
        ReviewState.PARTIAL,
        ReviewState.FAILED,
        ReviewState.CANCELLED,
    ],
)
def test_terminal_states_have_no_outbound_transition(terminal: ReviewState) -> None:
    for target in ReviewState:
        assert not can_transition(terminal, target)
