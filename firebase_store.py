import os
import requests
import random
import string

FIREBASE_URL = os.environ.get("FIREBASE_URL", "https://telebot-cbc1b-default-rtdb.firebaseio.com/")
def generate_random_key(length=6):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def generate_unique_key(data):
    while True:
        key = generate_random_key()
        if key not in data:
            return key

def save_file_id(file_id):
    print("🌐 [DEBUG] Saving file ID to Firebase...")
    all_data = get_all_data()
    key = generate_unique_key(all_data)

    url = f"{FIREBASE_URL}/file_ids/{key}.json"
    response = requests.put(url, json=file_id)
    if response.status_code == 200:
        return key
    else:
        print("❌ Error saving file ID:", response.text)
        return None

def get_file_id_by_key(key):
    url = f"{FIREBASE_URL}/file_ids/{key}.json"
    response = requests.get(url)
    if response.status_code == 200 and response.json():
        return response.json()
    return None

def get_all_data():
    url = f"{FIREBASE_URL}/file_ids.json"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json() or {}
    return {}

def has_seen_prompt(user_id: int) -> bool:
    url = f"{FIREBASE_URL}/prompt_users/{user_id}.json"
    response = requests.get(url)
    return response.status_code == 200 and response.json() is True

def mark_prompt_seen(user_id: int):
    url = f"{FIREBASE_URL}/prompt_users/{user_id}.json"
    response = requests.put(url, json=True)
    if response.status_code != 200:
        print(f"❌ Error saving prompt status: {response.text}")

def get_all_file_keys():
    print("🌐 [DEBUG] Fetching all file keys from Firebase...")
    all_data = get_all_data()
    return list(all_data.keys()) if all_data else []

