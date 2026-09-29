import json
from functools import lru_cache
from pathlib import Path

from pydantic import Field, model_validator

from app.sessions.models import Model, Text

PURPOSE_IDS = (
    "welcome-everyone",
    "set-the-agenda",
    "wrap-up",
    "share-progress",
    "ask-for-support",
    "ask-for-feedback",
    "start-a-conversation",
    "follow-up",
    "close-a-conversation",
)
SCENARIOS = ("hosting-a-meeting", "one-on-one", "casual-talk")


class Purpose(Model):
    purpose_id: str
    scenario_id: str
    order: int
    title: Text
    expression: Text
    alternative: Text
    explanation: Text
    example: Text
    hint_starter: Text
    preset_situation: Text
    learner_role: Text
    tutor_role: Text
    communication_goal: Text
    opening_direction: Text
    difficulty: str = "B1-B2"
    allowed_variations: list[str]
    integrated: bool = False


class Content(Model):
    version: str
    purposes: list[Purpose] = Field(min_length=9, max_length=9)
    rubric: dict[str, list[str]]

    @model_validator(mode="after")
    def ordered(self):
        if tuple(p.purpose_id for p in self.purposes) != PURPOSE_IDS:
            raise ValueError("Nine stable purpose IDs must appear in product order")
        for index, purpose in enumerate(self.purposes):
            if purpose.scenario_id != SCENARIOS[index // 3] or purpose.order != index:
                raise ValueError("Three purposes per scenario in product order required")
        return self


@lru_cache
def content() -> Content:
    path = Path(__file__).resolve().parents[3] / "content" / "workplace-english.json"
    # In the image content sits next to app; in the checkout it sits next to backend.
    if not path.exists():
        path = Path(__file__).resolve().parents[2] / "content" / "workplace-english.json"
    return Content.model_validate(json.loads(path.read_text(encoding="utf-8")))


def purpose(identifier: str) -> Purpose:
    return next(p for p in content().purposes if p.purpose_id == identifier)
