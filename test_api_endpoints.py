import requests
import json

# Base URL for the API
BASE_URL = "http://localhost:8000/api/v1"

def test_endpoint(endpoint: str, data: dict = None):
    """Test an API endpoint and print the response."""
    url = f"{BASE_URL}{endpoint}"
    print(f"\nTesting {endpoint}...")
    
    try:
        if data:
            response = requests.post(url, json=data)
        else:
            response = requests.post(url)
            
        print(f"Status Code: {response.status_code}")
        print("Response:")
        print(json.dumps(response.json(), indent=2))
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    # Test the health check endpoint
    print("Testing health check...")
    response = requests.get("http://localhost:8000/health")
    print(f"Health Check Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    # Test the API endpoints
    test_endpoint("/zapier/test/stripe_payout")
    test_endpoint("/zapier/test/incoming_wire")
    test_endpoint("/zapier/test/outgoing_ocbc")
    
    print("\nAPI testing complete!")
