import requests
import json
import time
import os
from typing import Dict, List, Optional
import uuid

# Configuration
BASE_URL = "https://app.swapcard.com/api/graphql"
AUTH_TOKEN = "YOUR_TOKEN_HERE"  # Replace with your actual token (e.g., Bearer <token>)
VIEW_ID = "VIEW_ID"  
EVENT_ID = "EVENT_ID"  
OUTPUT_FOLDER = "swapcard_data"  # Folder to store output

# Headers for API requests
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": AUTH_TOKEN  # Update to "Bearer <token>" if needed
}

def create_output_folder() -> None:
    """Create the output folder if it doesn't exist."""
    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)
        print(f"Created folder: {OUTPUT_FOLDER}")

def get_attendees(view_id: str, end_cursor: Optional[str] = None) -> Dict:
    """Fetch list of attendees with pagination."""
    query = {
        "operationName": "EventPeopleListViewConnectionQuery",
        "variables": {
            "viewId": view_id,
            "endCursor": end_cursor if end_cursor else None
        },
        "extensions": {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": "SHA_KEY" #replae this with your hash
            }
        }
    }
    
    print(f"Sending attendee list request with headers (Authorization redacted): Content-Type: {HEADERS['Content-Type']}")
    response = requests.post(BASE_URL, headers=HEADERS, json=[query])
    response.raise_for_status()
    response_data = response.json()
    
    # Save raw response to a file
    response_file = os.path.join(OUTPUT_FOLDER, f"raw_attendees_response_{uuid.uuid4().hex}.json")
    with open(response_file, "w", encoding="utf-8") as f:
        json.dump(response_data, f, indent=2)
    print(f"Saved raw attendees response to: {response_file}")
    print("Raw API response:", json.dumps(response_data, indent=2))
    
    if not response_data or not isinstance(response_data, list) or len(response_data) == 0:
        raise ValueError("Empty or invalid response structure")
    if "errors" in response_data[0]:
        raise ValueError(f"API error: {response_data[0]['errors']}")
    if "data" not in response_data[0]:
        raise ValueError("Response does not contain 'data' key")
    
    data = response_data[0]["data"]
    print("Keys in 'data':", list(data.keys()))
    
    if "view" not in data:
        raise ValueError("Response does not contain 'view' key")
    if "people" not in data["view"]:
        raise ValueError("Response does not contain 'people' key")
    
    return data

def get_attendee_details(person_id: str, user_id: str) -> Dict:
    """Fetch detailed information for a specific attendee."""
    query = {
        "operationName": "EventPersonDetailsQuery",
        "variables": {
            "skipMeetings": False,
            "withEvent": True,
            "withHostedBuyerView": False,
            "personId": person_id,
            "userId": user_id,
            "eventId": EVENT_ID,
            "viewId": ""
        },
        "extensions": {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": "SHA_KEY" #replae this with your hash
            }
        }
    }
    
    print(f"Sending details request for personId: {person_id}")
    response = requests.post(BASE_URL, headers=HEADERS, json=[query])
    response.raise_for_status()
    response_data = response.json()
    
    # Save raw response to a file
    response_file = os.path.join(OUTPUT_FOLDER, f"raw_details_response_{person_id}_{uuid.uuid4().hex}.json")
    with open(response_file, "w", encoding="utf-8") as f:
        json.dump(response_data, f, indent=2)
    print(f"Saved raw details response to: {response_file}")
    print(f"Attendee details response for {person_id}:", json.dumps(response_data, indent=2))
    
    if not response_data or not isinstance(response_data, list) or len(response_data) == 0:
        raise ValueError("Empty or invalid response structure")
    if "errors" in response_data[0]:
        raise ValueError(f"API error: {response_data[0]['errors']}")
    if "data" not in response_data[0]:
        raise ValueError("Response does not contain 'data' key")
    
    return response_data[0]["data"]

def main():
    create_output_folder()
    
    attendees_data = []
    end_cursor = None
    page_count = 0

    # Test person details query with known IDs from Postman
    test_person_id = "RXZlbnRQsZWWwbGVfNDEzODkzMDU="  # From your provided payload
    test_user_id = "VXNlcl8xN34BDE3MQ=="  # From your provided payload
    print("Testing person details query with known IDs...")
    try:
        test_details = get_attendee_details(test_person_id, test_user_id)
        attendees_data.append(test_details)
        print(f"Successfully fetched test details for person {test_person_id}")
    except Exception as e:
        print(f"Failed to fetch test details for person {test_person_id}: {str(e)}")

    # Fetch attendee list
    while True:
        print(f"Fetching page {page_count + 1}...")
        try:
            data = get_attendees(VIEW_ID, end_cursor)
        except Exception as e:
            print(f"Failed to fetch attendees: {str(e)}")
            break
        
        people = data["view"].get("people")
        if not people:
            print("No 'people' found in response")
            break
        
        nodes = people.get("nodes", [])
        if not nodes:
            print("No attendees found in this page")
        
        for node in nodes:
            if not node or "id" not in node or "userId" not in node:
                print("Invalid person data in node:", node)
                continue
            
            person_id = node["id"]  # Use node.id as personId
            user_id = node["userId"]  # Use node.userId as userId
            
            try:
                details = get_attendee_details(person_id, user_id)
                attendees_data.append(details)
                print(f"Fetched details for person {person_id}")
                time.sleep(0.5)  # Respect API rate limits
            except Exception as e:
                print(f"Error fetching details for person {person_id}: {str(e)}")
        
        page_count += 1
        end_cursor = people["pageInfo"]["endCursor"] if people.get("pageInfo") else None
        
        if not people.get("pageInfo", {}).get("hasNextPage", False):
            break
    
    if attendees_data:
        output_file = os.path.join(OUTPUT_FOLDER, f"attendees_{uuid.uuid4().hex}.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(attendees_data, f, indent=2)
        print(f"Scraped {len(attendees_data)} attendees. Data saved to {output_file}")
    else:
        print("No attendee data scraped.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"An error occurred: {str(e)}")
