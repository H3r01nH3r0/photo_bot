import json
import requests

AMPLITUDE_API_KEY = ""
AMPLITUDE_ENDPOINT = "https://api.amplitude.com/2/httpapi"

def statistics(user_id, event_name):
    amp_event = {
        "user_id": user_id,
        "event_type": event_name,
        "platform": 'photo_bot',
    }

    _ = requests.post(AMPLITUDE_ENDPOINT, data=json.dumps({
        'api_key': AMPLITUDE_API_KEY,
        'events': [amp_event],
    }))