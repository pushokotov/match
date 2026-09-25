import requests

from api.vars import HEADERS


def response_to_json(response):
    return response.json()


def requests_get(url):
    try:
        r = requests.get(url, headers=HEADERS)
        r.raise_for_status()
    except requests.exceptions.HTTPError as error:
        return error
    return r


def requests_post(url, data):
    try:
        r = requests.post(url, headers=HEADERS, data=data)
        r.raise_for_status()
    except requests.exceptions.HTTPError as error:
        return error
    return r
