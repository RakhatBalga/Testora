"""Response models for the read-only analytics, history, learning and vocabulary routers.

Envelopes and the stable fields are typed; payloads that are assembled from
several sources and evolve with the product are `dict[str, Any]`. All models
allow extra keys, so documenting a response never drops data from it.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict

Payload = dict[str, Any]


class _Open(BaseModel):
    model_config = ConfigDict(extra="allow")


class WeaknessOut(_Open):
    skill: str
    category: str
    subskill: str
    label: str
    score: float
    frequency: int
    avg_severity: float
    recent_frequency: int = 0
    window: int = 8
    recurring: bool


class WeaknessesOut(_Open):
    weaknesses: list[WeaknessOut]


class BlockerOut(_Open):
    skill: str
    criterion: str
    band_cap: float
    explanation: str
    fix_href: str


class BlockersOut(_Open):
    blockers: list[BlockerOut]


class BandGapOut(_Open):
    current: float | None
    target: float
    gap: float | None
    per_skill: dict[str, float]
    lowest_skill: str | None
    has_data: bool


class StreakOut(_Open):
    current_streak: int
    active_today: bool


class WeeklyWeakestOut(_Open):
    has_data: bool
    skill: str | None
    band: float | None
    attempts: int
    days: int


class DailyPlanTaskOut(_Open):
    id: str
    title: str
    detail: str
    skill: str | None
    href: str
    source: str
    estimated_minutes: int


class DailyPlanOut(_Open):
    generated_for: str
    has_data: bool
    plan: list[DailyPlanTaskOut]


class RecommendationOut(_Open):
    id: str
    title: str
    reason: str
    source: str
    skill: str | None
    priority: int
    estimated_impact: str
    href: str
    estimated_minutes: int


class RecommendationsOut(_Open):
    recommendations: list[RecommendationOut]


class RecurringMistakeOut(_Open):
    skill: str
    category: str
    subskill: str
    label: str
    occurrences: int
    window: int
    message: str


class RecurringMistakesOut(_Open):
    recurring: list[RecurringMistakeOut]


class HistoryPageOut(_Open):
    items: list[Payload]
    total: int
    page: int
    page_size: int
