import httpx
import json

def test_scraper():
    url = "http://localhost:8000/process"
    payload = {
        "task_id": "test-task-123",
        "agent_type": "web_scraper",
        "payload": {
            "url": "",
            "keyword": "",
            "raw_text": "https://id.wikipedia.org/wiki/Kecerdasan_buatan"
        }
    }
    
    print("Sending POST request to:", url)
    print("Payload:", json.dumps(payload, indent=2))
    
    try:
        response = httpx.post(url, json=payload, timeout=20.0)
        print("Status Code:", response.status_code)
        print("Response JSON:")
        print(json.dumps(response.json(), indent=2))
    except Exception as e:
        print("Error during request:", e)

if __name__ == "__main__":
    test_scraper()
