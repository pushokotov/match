from api.helpers import *
from api.vars import PROFILE_URL


def get_profile_info():
    j = response_to_json(requests_get(PROFILE_URL))
    position_info = j["data"]["user"]["pos_info"]
    if "state" in position_info:
        city = position_info["state"]["name"]
    elif "city" in position_info:
        city = position_info["city"]["name"]
    else:
        city = "Город не определен"
    country = position_info["country"]["name"]
    name = j["data"]["user"]["name"]
    d = {"city": city, "country": country, "user_name": name}
    return d
