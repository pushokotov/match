from app.tinder.models import MatchStats


class MatchService:
    def __init__(self, tinder_client):
        self.client = tinder_client

    def get_count(self) -> int:
        return self.client.get_matches_count()

    def snapshot(self) -> int:
        return self.get_count()

    def calculate(self, before: int, after: int) -> MatchStats:
        return MatchStats(before=before, after=after)
