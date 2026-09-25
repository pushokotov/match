import re
from typing import Any, Dict, Optional

import requests

from .models import Profile, Recommendation, TinderUser


class TinderAPIError(RuntimeError):
    pass


class TinderClient:
    """Low-level synchronous client for the Tinder HTTP API used by the project."""

    def __init__(self, base_url: str = "https://api.gotinder.com", locale: str = "ru", token: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.locale = locale
        self.session = requests.Session()
        self.session.headers.update({
            "x-supported-image-formats": "webp,jpeg",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.61 Safari/537.36",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "platform": "web",
        })
        if token:
            self.set_token(token)

    def set_token(self, token: str) -> None:
        self.session.headers["X-Auth-Token"] = token

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def _request(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        response = self.session.request(method, self._url(path), timeout=30, **kwargs)
        if not response.ok:
            raise TinderAPIError(
                f"Tinder API returned {response.status_code}: {response.text[:500]}"
            )
        return response

    def request_auth_phone(self, phone: str) -> requests.Response:
        payload = f"\n\x0e\n\x0c{phone.replace('+', '')}"
        return self._request("POST", f"/v3/auth/login?locale={self.locale}", data=payload)

    def authenticate_with_phone_code(self, phone: str, code: str) -> str:
        phone_payload = f"\n\x0e\n\x0c{phone.replace('+', '')}"
        payload = f"\x12\x18{phone_payload}\x12\x06{code}"
        response = self._request(
            "POST", f"/v3/auth/login?locale={self.locale}", data=payload
        )
        match = re.search(r"(\x12\$)(.*)(\"\x18)", response.text)
        if not match:
            raise TinderAPIError(
                "Tinder authentication response did not contain an auth token"
            )
        token = match.group(2)
        self.set_token(token)
        return token

    def authenticate_with_token(self, token: str) -> None:
        self.set_token(token)

    def get_profile(self) -> Profile:
        path = (
            "/v2/profile?locale={}"
            "&include=account%2Cboost%2Ccontact_cards%2Cemail_settings%2Cinstagram%2C"
            "likes%2Cnotifications%2Cplus_control%2Cproducts%2Cpurchase%2Creadreceipts%2C"
            "swipenote%2Cspotify%2Csuper_likes%2Ctinder_u%2Ctravel%2Ctutorials%2Cuser"
        ).format(self.locale)
        data = self._request("GET", path).json()["data"]["user"]
        position = data.get("pos_info", {})
        if "state" in position:
            city = position["state"]["name"]
        elif "city" in position:
            city = position["city"]["name"]
        else:
            city = "Город не определен"
        country = position.get("country", {}).get("name", "")
        return Profile(name=data.get("name", ""), city=city, country=country)

    def set_location(self, latitude: float, longitude: float) -> None:
        self._request(
            "POST",
            f"/v2/meta?locale={self.locale}",
            json={"lat": latitude, "lon": longitude, "force_fetch_resources": True},
        )

    def get_recommendations(self) -> list[Recommendation]:
        data = self._request(
            "GET", f"/v2/recs/core?locale={self.locale}"
        ).json().get("data", {})
        recommendations = []
        for item in data.get("results", []):
            user = item.get("user", {})
            user_id = user.get("_id")
            if not user_id:
                continue
            recommendations.append(
                Recommendation(
                    user=TinderUser(
                        id=user_id,
                        name=user.get("name", ""),
                        photos=user.get("photos", []),
                        raw=user,
                    ),
                    s_number=item.get("s_number"),
                    raw=item,
                )
            )
        return recommendations

    def like(self, user_id: str) -> None:
        self._request("POST", f"/like/{user_id}?locale={self.locale}")

    def dislike(self, user_id: str, s_number: Optional[int] = None) -> None:
        path = f"/pass/{user_id}?locale={self.locale}"
        if s_number is not None:
            path += f"&s_number={s_number}"
        self._request("GET", path)

    def get_matches_count(self) -> int:
        return len(self._get_all_matches())

    def _get_all_matches(self) -> list[Dict[str, Any]]:
        matches = []
        page_token = None
        while True:
            path = f"/v2/matches?locale={self.locale}&count=100&is_tinder_u=false"
            if page_token:
                path += f"&page_token={page_token}"
            data = self._request("GET", path).json().get("data", {})
            matches.extend(data.get("matches", []))
            page_token = data.get("next_page_token")
            if not page_token:
                return matches
