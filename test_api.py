import requests
import json

def test_api():
    try:
        response = requests.get('http://localhost:8000')
        print(f"Root endpoint status: {response.status_code}")
        
        test_data = {"username": "octocat"}
        response = requests.post('http://localhost:8000/search', json=test_data)
        print(f"Shallow search status: {response.status_code}")
        if response.status_code != 200:
            print(f"Error: {response.text}")
            return

        candidates = response.json()
        print("Candidates:")
        print(json.dumps(candidates, indent=2, default=str))

        if not candidates:
            print("No candidates to enrich.")
            return

        candidate = candidates[0]
        response = requests.post('http://localhost:8000/profile/enrich', json=candidate)
        print(f"Deep enrich status: {response.status_code}")
        if response.status_code == 200:
            profile = response.json()
            print("FinalProfile:")
            print(json.dumps(profile, indent=2, default=str))
        else:
            print(f"Error: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("Could not connect to server. Make sure it's running on localhost:8000")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_api()