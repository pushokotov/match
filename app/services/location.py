from geopy import Nominatim


class LocationService:
    def __init__(self, tinder_client, user_agent: str = "tinder-refactor"):
        self.client = tinder_client
        self.geolocator = Nominatim(user_agent=user_agent)

    def set_city(self, city: str):
        location = self.geolocator.geocode(city)
        if location is None:
            raise ValueError(f"City not found: {city}")
        self.client.set_location(location.latitude, location.longitude)
        return location
