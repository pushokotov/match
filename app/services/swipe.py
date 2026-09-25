import time
from typing import Iterable, Set

from config import SWIPE_LIMIT
from app.tinder.models import Recommendation, SwipeResult


class SwipeService:
    def __init__(self, tinder_client, recommendation_service, swipe_limit: int = SWIPE_LIMIT, delay_seconds: float = 0.0):
        self.client = tinder_client
        self.recommendations = recommendation_service
        self.swipe_limit = swipe_limit
        self.delay_seconds = delay_seconds

    def run(self, first_batch: Iterable[Recommendation]) -> SwipeResult:
        swipes = likes = dislikes = 0
        seen: Set[str] = set()
        batch = list(first_batch)
        exhausted = False

        while swipes < self.swipe_limit:
            if not batch:
                batch = self.recommendations.get_batch()
                if not batch:
                    exhausted = True
                    break

            for recommendation in batch:
                if swipes >= self.swipe_limit:
                    break
                if recommendation.user.id in seen:
                    continue
                seen.add(recommendation.user.id)

                if len(recommendation.user.photos) >= 2:
                    self.client.like(recommendation.user.id)
                    likes += 1
                else:
                    self.client.dislike(recommendation.user.id, recommendation.s_number)
                    dislikes += 1
                swipes += 1

                if self.delay_seconds:
                    time.sleep(self.delay_seconds)

            batch = []

        return SwipeResult(
            swipes=swipes,
            likes=likes,
            dislikes=dislikes,
            limit_reached=swipes >= self.swipe_limit,
            recommendations_exhausted=exhausted,
        )
