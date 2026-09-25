class ProfileService:
    def __init__(self, tinder_client):
        self.client = tinder_client

    def get_profile(self):
        return self.client.get_profile()
