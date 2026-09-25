import uuid

TELEGRAM_TOKEN = "your_tg_token"
TELEGRAM_TOKEN_TEST = "your_tg_token"
LOCALE = "ru"
SWIPE_LIMIT = 100
API_URL = f"https://api.gotinder.com"
AUTH_CODE_REQUEST_URL = f"{API_URL}/v3/auth/login?locale={LOCALE}"
RECS_URL = f"{API_URL}/v2/recs/core?locale={LOCALE}"
GEO_META_URL = f"{API_URL}/v2/meta?locale={LOCALE}"
MATCHES_URL = f"{API_URL}/v2/matches?locale={LOCALE}"
PROFILE_URL = f"{API_URL}/v2/profile?locale={LOCALE}&include=account%2Cboost%2Ccontact_cards%2Cemail_settings%2Cinstagram%2Clikes%2Cnotifications%2Cplus_control%2Cproducts%2Cpurchase%2Creadreceipts%2Cswipenote%2Cspotify%2Csuper_likes%2Ctinder_u%2Ctravel%2Ctutorials%2Cuser"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.61 Safari/537.36"
DEVICE_ID = str(uuid.uuid1())
HEADERS = {'x-supported-image-formats': 'webp,jpeg', 'user-agent': USER_AGENT,
           'Accept': 'application/json',
           'content-type': 'application/x-google-protobuf',
           'persistent-device-id': DEVICE_ID,
           'Content-Type': 'application/json',
           'platform': 'web',
           'Accept-Encoding': 'gzip, deflate, br'
           }
