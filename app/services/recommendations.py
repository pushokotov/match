class RecommendationService:
    def __init__(self, tinder_client):
        self.client = tinder_client

    def get_batch(self):
        return self.client.get_recommendations()
