from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class TinderUser:
    id: str
    name: str
    photos: List[Dict[str, Any]]
    raw: Dict[str, Any]


@dataclass(frozen=True)
class Recommendation:
    user: TinderUser
    s_number: Optional[int]
    raw: Dict[str, Any]


@dataclass(frozen=True)
class Profile:
    name: str
    city: str
    country: str


@dataclass(frozen=True)
class SwipeResult:
    swipes: int
    likes: int
    dislikes: int
    limit_reached: bool
    recommendations_exhausted: bool


@dataclass(frozen=True)
class MatchStats:
    before: int
    after: int

    @property
    def new_matches(self) -> int:
        return max(0, self.after - self.before)
