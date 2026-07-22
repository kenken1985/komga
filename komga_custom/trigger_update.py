import os
import sys
import json
import requests
from urllib.parse import urljoin

def trigger_update(series_name, library_id):
    """
    Trigger a manual update for a series via the Automaga API
    
    Args:
        series_name (str): Name of the series to update
        library_id (str): ID of the library to determine media type
    """
    # Get AUTOMANGA_URL from environment variable
    AUTOMANGA_URL = os.environ.get('AUTOMANGA_URL')
    if not AUTOMANGA_URL:
        print("Error: AUTOMANGA_URL environment variable not found")
        return False

    # Determine media type based on library ID
    if library_id == "0FK57Y46H30NY":
        media_type = "MANGA"
    elif library_id == "0FK584ET13AGD":
        media_type = "NOVEL"
    else:
        print(f"Warning: Unknown library ID {library_id}")
        return False

    # Prepare the API endpoint
    api_endpoint = urljoin(AUTOMANGA_URL, "/api/trigger/manual-update")

    # Prepare the payload
    payload = {
        "series_name": series_name,
        "mode": "nyaa+dlraw",
        "media_type": media_type,
        "add_new_series": "None",
        "options": {
            "dry_run": False
        }
    }

    try:
        # Make the API request
        response = requests.post(
            api_endpoint,
            json=payload,
            headers={'Content-Type': 'application/json'}
        )
        
        # Check if request was successful
        if response.status_code == 200:
            print(f"Successfully triggered update for series '{series_name}' in library '{library_id}'")
            return True
        else:
            print(f"Failed to trigger update. Status code: {response.status_code}, Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"Error making API request: {str(e)}")
        return False

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python trigger_update.py <series_name> <library_id>")
        sys.exit(1)
    
    series_name = sys.argv[1]
    library_id = sys.argv[2]
    
    success = trigger_update(series_name, library_id)
    sys.exit(0 if success else 1)