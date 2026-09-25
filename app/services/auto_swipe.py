from dataclasses import dataclass

from app.services.matches import MatchService
from app.services.recommendations import RecommendationService
from app.services.swipe import SwipeService


@dataclass(frozen=True)
class AutoSwipeResult:
    swipe_result: object
    match_stats: object
    recommendations_received: int
    location: object


class AutoSwipeService:
    """Orchestrates one complete AutoSwipe run."""

    def __init__(
        self,
        location_service,
        recommendation_service: RecommendationService,
        match_service: MatchService,
        swipe_service: SwipeService,
    ):
        self.location_service = location_service
        self.recommendations = recommendation_service
        self.matches = match_service
        self.swipes = swipe_service

    def run(self, city: str) -> AutoSwipeResult:
        location = self.location_service.set_city(city)

        # The first recommendation batch is deliberately fetched before
        # taking the match snapshot and before any swipe is performed.
        first_batch = self.recommendations.get_batch()
        before = self.matches.snapshot()

        swipe_result = self.swipes.run(first_batch)
        after = self.matches.snapshot()
        match_stats = self.matches.calculate(before, after)

        return AutoSwipeResult(
            swipe_result=swipe_result,
            match_stats=match_stats,
            recommendations_received=len(first_batch),
            location=location,
        )
