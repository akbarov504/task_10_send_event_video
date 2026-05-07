import os
import json
import fcntl
import requests
from datetime import datetime, timedelta
from core.config import TOKEN_FILE_PATH, API_BASE_STREAM, TOKEN_REFRESH_MARGIN
from typing import Optional


# CONFIGURATION
REGISTER_ENDPOINT = f"{API_BASE_STREAM}/mini-pcs/register"
AUTH_ENDPOINT = f"{API_BASE_STREAM}/truck/authenticate"

def safe_read_json(path: str) -> dict:
    """Safely read JSON with shared lock."""
    if not os.path.exists(path):
        return {}
    with open(path, "r") as f:
        fcntl.flock(f, fcntl.LOCK_SH)
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            data = {}
        fcntl.flock(f, fcntl.LOCK_UN)
        return data


def safe_write_json(path: str, data: dict):
    """Safely write JSON with exclusive lock."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        json.dump(data, f, indent=2)
        fcntl.flock(f, fcntl.LOCK_UN)


# TOKEN MANAGEMENT
def get_token_info() -> dict:
    """Returns the current token info from file (if exists)."""
    data = safe_read_json(TOKEN_FILE_PATH)
    return data


def save_token_info(token: str, expires_at: str, truck_id: int):
    """Stores new token info safely in JSON file."""
    data = {
        "token": token,
        "truck_id": truck_id,
        "expires_at": expires_at,
        "updated_at": datetime.now().isoformat() + "Z",
    }
    safe_write_json(TOKEN_FILE_PATH, data)
    print(f"[TOKEN_MANAGER] Token saved. Expires at: {expires_at}")


def is_token_expired() -> bool:
    """Checks if token is expired or near expiry."""
    data = get_token_info()
    expires_at = data.get("expires_at")
    if not expires_at:
        return True
    try:
        expire_dt = datetime.fromisoformat(expires_at.split('.')[0])
        return (expire_dt - datetime.now()).total_seconds() < TOKEN_REFRESH_MARGIN
    except Exception as e:
        return True


# REGISTRATION & AUTH
def register_mini_pc(mac_address: str, serial_number: str, truck_info: dict) -> dict:
    """Registers MiniPC and retrieves truckId."""
    payload = {
        "macAddress": mac_address,
        "serialNumber": serial_number,
        "truck": truck_info,
    }
    print("[TOKEN_MANAGER] Registering MiniPC...")
    response = requests.post(REGISTER_ENDPOINT, json=payload)
    if response.status_code == 200:
        data = response.json()
        print(f"[TOKEN_MANAGER] Registered. Truck ID: {data.get('truck').get('id')}")
        return data
    else:
        raise Exception(f"Registration failed: {response.status_code} {response.text}")


def authenticate_truck(truck_id: int) -> dict:
    """Authenticates truck using truckId and returns token info."""
    payload = {"truckId": truck_id}
    print(f"[TOKEN_MANAGER] Authenticating truck ID {truck_id}...")
    response = requests.post(AUTH_ENDPOINT, json=payload)
    if response.status_code == 200:
        data = response.json()
        save_token_info(
            data.get("id_token"),
            data.get("expires_at"),
            truck_id
        )
        return data
    else:
        raise Exception(f"Authentication failed: {response.status_code} {response.text}")


def get_valid_token() -> Optional[str]:
    """
    Return a valid token. If token absent or near expiry, try to refresh.
    If refresh fails due to network, return the existing token (best-effort).
    If no token at all, raise.
    """
    info = get_token_info()
    token = info.get("token")
    truck_id = info.get("truck_id")

    # If token is present and not near expiry -> just return it
    if token and not is_token_expired():
        return token

    # Need to refresh. If we don't have truck_id we cannot refresh
    if not truck_id:
        raise Exception("Cannot refresh token: truck_id not found. Register the MiniPC first.")

    # Try refreshing, but handle network problems gracefully and fallback to current token
    try:
        new_info = authenticate_truck(truck_id)
        # authenticate_truck saved token to disk; return it
        stored = get_token_info()
        return stored.get("token")
    except requests.exceptions.RequestException as e:
        # network-related error: warn and return existing token if any
        print(f"[TOKEN_MANAGER] Token refresh failed due to network: {e}. Falling back to stored token (if any).")
        if token:
            return token
        else:
            raise
    except Exception as e:
        # other errors (bad response etc.)
        print(f"[TOKEN_MANAGER] Token refresh failed: {e}")
        if token:
            return token
        raise