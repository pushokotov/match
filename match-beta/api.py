import asyncio
from datetime import datetime
import random

import geocoder as geocoder
import requests
import re
import time
import json
import uuid

from geopy import Nominatim

from vars import PROFILE_URL, MATCHES_URL, HEADERS, AUTH_CODE_REQUEST_URL, RECS_URL, API_URL, LOCALE, USER_AGENT, \
    GEO_META_URL

DISLIKED_ID_LIST = set()
ALREADY_LIKED_ID_LIST = set()
SORTED_ID_LIST = set()


class BOT:
    LIKE_RESULT = {}
    LIKE_COUNTER = 0
    COLLECTED_NUMBER = 0
    PROFILE_PURCHASES = None

    @staticmethod
    def auth_with_token():
        token = input("Enter auth token: ")
        HEADERS.update({'X-Auth-Token': token})

    @staticmethod
    def tg_auth_with_token(token):
        HEADERS.update({'X-Auth-Token': token})

    def post_phone_number(self, phone_number):
        # self.requests_post(AUTH_CODE_REQUEST_URL, f"\n\u000e\n\f{phone_number}")
        phone_number_data = f"\n\u000e\n\f{phone_number}"
        r = self.requests_post(AUTH_CODE_REQUEST_URL, phone_number_data)

    def auth_with_phone_number(self):
        phone_number = input("Enter your phone number: ")
        phone_number_data = f"\n\u000e\n\f{phone_number}"
        r = self.requests_post(AUTH_CODE_REQUEST_URL, phone_number_data)
        received_code = input("Enter code received from sms: ")
        code_data = f"\u0012\u0018{phone_number_data}\u0012\u0006{received_code}"
        r2 = self.requests_post(AUTH_CODE_REQUEST_URL, code_data)
        token = re.search('(\x12\$)(.*)("\x18)', r2.text)[2]
        print(r2, token)
        HEADERS.update({'X-Auth-Token': token})

    def tg_post_auth_code(self, phone_number, code):
        return self.tg_requests_post(AUTH_CODE_REQUEST_URL,
                                     f"\u0012\u0018\n\u000e\n\f{phone_number.replace('+', '')}\u0012\u0006{code}")

    @staticmethod
    def tg_generate_token(r):
        token = re.search('(\x12\$)(.*)("\x18)', r.text)[2]
        print(r, token)
        HEADERS.update({'X-Auth-Token': token})

    def tg_auth_enter_phone_number(self, phone_number):
        phone_number_data = f"\n\u000e\n\f{phone_number.replace('+', '')}"
        r = self.tg_requests_post(AUTH_CODE_REQUEST_URL, phone_number_data)
        return r

    def tg_auth_with_phone_number(self, phone_number, sms_code):
        phone_number_data = f"\n\u000e\n\f{phone_number}"
        r = self.requests_post(AUTH_CODE_REQUEST_URL, phone_number_data)
        code_data = f"\u0012\u0018{phone_number_data}\u0012\u0006{sms_code}"
        r2 = self.requests_post(AUTH_CODE_REQUEST_URL, code_data)
        token = re.search('(\x12\$)(.*)("\x18)', r2.text)[2]
        print(r2, token)
        HEADERS.update({'X-Auth-Token': token})

    @staticmethod
    def response_to_json(response):
        return response.json()

    @staticmethod
    def requests_get(url):
        try:
            r = requests.get(url, headers=HEADERS)
            r.raise_for_status()
        except requests.exceptions.HTTPError as error:
            return error
        return r

    @staticmethod
    async def r_get(url):
        async with requests.get(url, HEADERS) as response:
            assert response.status == 200
            return await response

    @staticmethod
    async def r_post(url, payload):
        async with requests.post(url, headers=HEADERS, data=payload) as request:
            assert request.status == 200
            return await request.read()

    @staticmethod
    def requests_post(url, data):
        try:
            r = requests.post(url, headers=HEADERS, data=data)
            r.raise_for_status()
        except requests.exceptions.HTTPError as error:
            return error
        return r

    @staticmethod
    def tg_requests_post(url, data):
        return requests.post(url, headers=HEADERS, data=data)

    def tg_get_new_matches_count(self):
        j = self.get_all_matches_json(100, None)
        results = j["data"]["matches"]
        i = 0
        for each in results:
            if not each["seen"]["match_seen"]:
                i += 1
        return i

    def tg_get_profile_info(self):
        self.get_profile_purchases()
        j = self.response_to_json(self.requests_get(PROFILE_URL))
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

    def get_profile_purchases(self):
        j = self.response_to_json(self.requests_get(PROFILE_URL))
        purchase_obj = j['data']['purchase']
        purchases = purchase_obj['purchases']
        if len(purchases) >= 1:
            self.PROFILE_PURCHASES = True
        else:
            self.PROFILE_PURCHASES = False

    def get_all_matches_json(self, count, page_token):
        url = MATCHES_URL + '&count=' + str(count) + '&is_tinder_u=false'
        if page_token:
            url = url + '&page_token=' + page_token
        j = self.response_to_json(self.requests_get(url))
        if 'data' in j.keys() and 'next_page_token' in j['data'].keys():
            next_page_data = self.get_all_matches_json(count, j['data']['next_page_token'])
            j['data']['matches'] = j['data']['matches'] + next_page_data['data']['matches']
        return j

    def tg_get_all_matches_count(self):
        j = self.get_all_matches_json(100, None)
        return len(j['data']['matches'])

    def get_recomendations_results(self, location):
        r = self.requests_get(RECS_URL)
        if r.status_code == 200:
            recs_json = r.json()
            if 'results' in recs_json['data']:
                results = recs_json['data']['results']
                print(f"{datetime.now()} : Bot have found {len(results)} results in {location}")
                return results
            print(f"{datetime.now()} : Bot have found no results in {location}")
            return {}
        return r

    def sort_results(self, results):
        n = len(results)
        for each in results:
            user = each['user']
            user_id = user['_id']
            if user_id not in SORTED_ID_LIST:
                SORTED_ID_LIST.add(user_id)
                self.COLLECTED_NUMBER += 1

    def get_dislike(self, url, user_id):
        r = self.requests_get(url)
        if r.status_code == 200:
            DISLIKED_ID_LIST.add(user_id)
        else:
            print(f"brrraaaaa -  {user_id}")

    def post_like(self, url, user_id):
        i = 0
        try:
            r = requests.post(url, headers=HEADERS)
            r.raise_for_status()
        except requests.exceptions.HTTPError as error:
            return print(f"Unable to post like for {user_id}. \n Error text: {error}")
        if r.status_code == 200:
            self.LIKE_COUNTER += 1
            print(f"user with Id {user_id} was liked")
        else:
            print(f"brrraaaaa -  {user_id}")

    @staticmethod
    def update_liked_id_list(user_id):
        ALREADY_LIKED_ID_LIST.add(user_id)

    def swipe(self, results, location):
        a = 0
        n = len(results)
        print(f"length of the list is {len(results)}")
        for each in results:
            # while self.LIKE_RESULT <= 100:
            random_photo = random.choice(each['user']['photos'])
            user = each['user']
            user_id = user['_id']
            s_number = each["s_number"]
            request_body = f'{{"s_number":{s_number},"liked_content_id":"{random_photo["id"]}","liked_content_type":"photo"}}'
            if user_id not in ALREADY_LIKED_ID_LIST or DISLIKED_ID_LIST:
                if len(each['user']['photos']) < 2:
                    dislike_url = f"{API_URL}/pass/{user_id}?locale={LOCALE}&s_number={s_number}"
                    self.get_dislike(dislike_url, user_id)
                    print(f"disliked {user_id}")
                elif len(each['user']['photos']) >= 2:
                    like_url = f"{API_URL}/like/{user_id}?locale={LOCALE}"
                    self.post_like(like_url, user_id)
                    self.update_liked_id_list(user_id)
                    a += 1
                    self.LIKE_RESULT.update({location: a})
                    print(f"like result - {self.LIKE_RESULT}")
            time.sleep(random.randint(0, 5))
        else:
            print(f"user was already swiped")

    def repeat(self, string_to_expand, length):
        return print(string_to_expand * (int(length / len(string_to_expand)) + 1))[:length]

    def get_location_data(self, city):
        geolocator = Nominatim(user_agent=USER_AGENT)
        location = geolocator.geocode(city)
        return location

    def get_coordinates_withing_city(self, city):
        g = geocoder.osm(city)
        r_json = g.json
        northeast_lat = r_json['bbox']['northeast'][0]
        northeast_long = r_json['bbox']['northeast'][1]
        southwest_lat = r_json['bbox']['southwest'][0]
        southwest_long = r_json['bbox']['southwest'][1]
        random_lat = round(random.uniform(northeast_lat, southwest_lat), 7)
        random_long = round(random.uniform(northeast_long, southwest_long), 7)
        return random_lat, random_long

    def post_geo_meta(self, city):
        location = self.get_location_data(city)
        request_body = f"{{\"lat\":{str(location.latitude)},\"lon\":{str(location.longitude)},\"force_fetch_resources\":true}}"
        r = self.requests_post(GEO_META_URL, request_body)
        print(f"New Location {city} : {r}")
        return r

    def post_geo_meta_within_city_bounds(self, location):
        request_body = f"{{\"lat\":{str(location[0])},\"lon\":{str(location[1])},\"force_fetch_resources\":true}}"
        self.requests_post(GEO_META_URL, request_body)

    def set_location_list(self):
        final_list = [item for item in input("Enter a list of cities to collects users from: ").split(', ')]
        return final_list

    def tg_set_location_list(self, locations):
        final_list = [item for item in locations.split(', ')]
        return final_list

    def switch_location(self, location):
        desired_location = self.get_location_data(location)
        self.post_geo_meta(desired_location)

    def change_location(self, location):
        location = self.get_coordinates_withing_city(location)
        self.post_geo_meta_within_city_bounds(location)
        return f"New location: {location}"

    def get_updates(self, token):
        HEADERS.update({'X-Auth-Token': token})

    def tg_run(self, location):
        location = self.tg_set_location_list(location)
        self.run(location)
        return self.LIKE_RESULT

    def run(self, location):
        for each in location:
            self.change_location(each)
            results = self.get_recomendations_results(each)
            if results:
                self.swipe(results, each)

    def tg_get_nearest_recs(self, location):
        return len(self.get_recomendations_results(location))

    def collect_recommendations(self):
        location = self.set_location_list()
        for each in location:
            print(each)
            while self.COLLECTED_NUMBER <= 1000:
                new_location = self.change_location(each)
                print(new_location)
                results = self.get_recomendations_results(new_location)
                self.sort_results(results)
                # TODO: create dict and put location : collected_number
                print(
                    f"Number of collected users is {self.COLLECTED_NUMBER} \n at {location} : {new_location}")

    def tg_collect_recommendations(self, location, limit):
        for each in location:
            print(each)
            while self.COLLECTED_NUMBER <= limit:
                new_location = self.change_location(each)
                print(new_location)
                results = self.get_recomendations_results(new_location)
                self.sort_results(results)
                # TODO: create dict and put location : collected_number
                print(
                    f"Number of collected users is {self.COLLECTED_NUMBER} \n at {location} : {new_location}")
        return self.COLLECTED_NUMBER

# if __name__ == "__main__":
#     asyncio.run(post_phone_number(input("input phone number: ")))
