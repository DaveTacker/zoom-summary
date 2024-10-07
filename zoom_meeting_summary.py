"""Module for processing and summarizing Zoom meeting data."""

import json
import logging
import os
from datetime import datetime, timedelta
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from dateutil import parser
from config import CLIENT_ID, CLIENT_SECRET, ACCOUNT_ID
from tqdm import tqdm

# Set up logging
log_filename = f"zoom_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
    ]
)

# Console logger
console = logging.getLogger('console')
console.setLevel(logging.INFO)
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(message)s'))
console.addHandler(console_handler)

# Auth cache file
AUTH_CACHE_FILE = "auth_cache.json"

# Set up requests session with retry logic
session = requests.Session()
retries = Retry(total=5, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
session.mount('https://', HTTPAdapter(max_retries=retries))

def log_response(response):
    logging.info(f"Response Status Code: {response.status_code}")
    logging.info(f"Response Headers: {json.dumps(dict(response.headers), indent=2)}")
    try:
        logging.info(f"Response Content: {json.dumps(response.json(), indent=2)}")
    except json.JSONDecodeError:
        logging.info(f"Response Content (non-JSON): {response.text}")

def load_cached_token():
    if os.path.exists(AUTH_CACHE_FILE):
        with open(AUTH_CACHE_FILE, 'r') as f:
            cache = json.load(f)
        expiration = datetime.fromisoformat(cache['expiration'])
        if expiration > datetime.now():
            logging.info("Using cached access token")
            return cache['access_token']
    return None

def save_token_to_cache(access_token, expires_in):
    expiration = datetime.now() + timedelta(seconds=expires_in)
    cache = {
        'access_token': access_token,
        'expiration': expiration.isoformat()
    }
    with open(AUTH_CACHE_FILE, 'w') as f:
        json.dump(cache, f)
    logging.info("Saved access token to cache")

def get_access_token():
    cached_token = load_cached_token()
    if cached_token:
        return cached_token

    url = "https://zoom.us/oauth/token"
    data = {
        "grant_type": "account_credentials",
        "account_id": ACCOUNT_ID,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    }
    try:
        response = session.post(url, data=data, timeout=10)
        response.raise_for_status()
        log_response(response)
        token_data = response.json()
        access_token = token_data["access_token"]
        expires_in = token_data["expires_in"]
        save_token_to_cache(access_token, expires_in)
        logging.info("Successfully obtained new access token")
        return access_token
    except requests.exceptions.RequestException as e:
        logging.error(f"Error obtaining access token: {e}")
        log_response(response)
        raise Exception("Failed to obtain access token")

def get_user_id(access_token):
    url = "https://api.zoom.us/v2/users/me"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    try:
        response = session.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        log_response(response)
        user_id = response.json()["id"]
        logging.info(f"Successfully obtained user ID: {user_id}")
        return user_id
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to obtain user ID: {e}")
        log_response(response)
        raise Exception("Failed to obtain user ID")

def get_meeting_details(access_token, meeting_id):
    url = f"https://api.zoom.us/v2/meetings/{meeting_id}"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        log_response(response)
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to fetch meeting details for meeting {meeting_id}: {e}")
        log_response(response)
        return None

def get_meetings(access_token, user_id, start_date, end_date):
    url = f"https://api.zoom.us/v2/users/{user_id}/meetings"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    params = {
        "type": "scheduled",
        "page_size": 300,
        "from": start_date.isoformat(),
        "to": end_date.isoformat()
    }
    meetings = []
    try:
        while True:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            log_response(response)
            data = response.json()
            meetings.extend(data["meetings"])
            if "next_page_token" in data and data["next_page_token"]:
                params["next_page_token"] = data["next_page_token"]
            else:
                break
        logging.info(f"Successfully fetched {len(meetings)} meetings")
        return meetings
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to fetch meetings: {e}")
        log_response(response)
        raise Exception("Failed to fetch meetings")

def get_meeting_participants(access_token, meeting_id):
    url = f"https://api.zoom.us/v2/report/meetings/{meeting_id}/participants"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    params = {
        "page_size": 300
    }
    participants = []
    try:
        while True:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            log_response(response)
            data = response.json()
            participants.extend(data["participants"])
            if "next_page_token" in data and data["next_page_token"]:
                params["next_page_token"] = data["next_page_token"]
            else:
                break
        logging.info(f"Successfully fetched {len(participants)} participants for meeting {meeting_id}")
        return participants
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to fetch participants for meeting {meeting_id}: {e}")
        log_response(response)
        return []

def calculate_participant_duration(join_time, leave_time):
    join = parser.parse(join_time)
    leave = parser.parse(leave_time)
    duration = leave - join
    return int(duration.total_seconds() / 60)  # Duration in minutes

def summarize_meetings(access_token, meetings):
    summary = []
    for meeting in tqdm(meetings, desc="Processing meetings", unit="meeting"):
        start_time = parser.parse(meeting["start_time"])
        scheduled_duration = meeting["duration"]
        end_time = start_time + timedelta(minutes=scheduled_duration)
        
        participants = get_meeting_participants(access_token, meeting["id"])
        participant_summaries = []
        for participant in participants:
            duration = calculate_participant_duration(participant["join_time"], participant["leave_time"])
            participant_summaries.append({
                "name": participant["name"],
                "email": participant.get("email", "N/A"),
                "duration": f"{duration} minutes"
            })
        
        summary.append({
            "topic": meeting["topic"],
            "start_time": start_time.strftime("%Y-%m-%d %H:%M"),
            "end_time": end_time.strftime("%Y-%m-%d %H:%M"),
            "scheduled_duration": f"{scheduled_duration} minutes",
            "participants": participant_summaries
        })
    logging.info(f"Summarized {len(summary)} meetings")
    return summary

def main():
    try:
        console.info("Starting Zoom meeting summary script")
        access_token = get_access_token()
        console.info("[OK] Authenticated")
        
        user_id = get_user_id(access_token)
        console.info("[OK] Fetched user info")
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=14)
        
        console.info(f"Fetching meetings from {start_date.date()} to {end_date.date()}")
        meetings = get_meetings(access_token, user_id, start_date, end_date)
        console.info(f"[OK] Fetched {len(meetings)} meetings")
        
        summary = summarize_meetings(access_token, meetings)
        
        console.info(f"\nMeeting summary for the last two weeks ({start_date.date()} to {end_date.date()}):")
        console.info(json.dumps(summary, indent=2))
        console.info("Script completed successfully")
    except Exception as e:
        console.exception(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
