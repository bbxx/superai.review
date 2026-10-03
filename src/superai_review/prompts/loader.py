from enum import StrEnum
from pathlib import Path

_ROOT = Path(__file__).resolve().parent


class PromptName(StrEnum):
    COMMON = "common"
    PROPOSER_ANALYST = "proposer-analyst"
    PROPOSER_CHALLENGER = "proposer-challenger"
    PROPOSER_STRATEGIST = "proposer-strategist"
    PROPOSER_INDEPENDENT = "proposer-independent"
    CROSS_REVIEW = "cross-review"
    DEBATE = "debate"
    JUDGE = "judge"
    FINAL_CRITIC = "final-critic"
    REPAIR = "repair"


_FILES: dict[PromptName, str] = {
    PromptName.COMMON: "common.md",
    PromptName.PROPOSER_ANALYST: "proposer-analyst.md",
    PromptName.PROPOSER_CHALLENGER: "proposer-challenger.md",
    PromptName.PROPOSER_STRATEGIST: "proposer-strategist.md",
    PromptName.PROPOSER_INDEPENDENT: "proposer-independent.md",
    PromptName.CROSS_REVIEW: "cross-review.md",
    PromptName.DEBATE: "debate.md",
    PromptName.JUDGE: "judge.md",
    PromptName.FINAL_CRITIC: "final-critic.md",
    PromptName.REPAIR: "repair.md",
}


def load_prompt(name: PromptName) -> str:
    return (_ROOT / _FILES[name]).read_text(encoding="utf-8").strip()


def compose_prompt(name: PromptName) -> str:
    if name is PromptName.COMMON:
        return load_prompt(name)
    return f"{load_prompt(PromptName.COMMON)}\n\n{load_prompt(name)}"
