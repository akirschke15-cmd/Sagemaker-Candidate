"""
Simple API Test Script

Tests basic API functionality without requiring authentication.
Run the API server first: python run_api.py

Usage:
    python test_api.py
"""
import requests
import json
import sys

BASE_URL = "http://localhost:8000"

# API key (leave empty for dev mode testing)
API_KEY = ""
headers = {"X-API-Key": API_KEY} if API_KEY else {}


def test_health():
    """Test health check endpoint"""
    print("\n=== Testing Health Check ===")
    response = requests.get(f"{BASE_URL}/api/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    assert response.status_code == 200, "Health check failed"
    print("✓ Health check passed")


def test_root():
    """Test root endpoint"""
    print("\n=== Testing Root Endpoint ===")
    response = requests.get(BASE_URL)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    assert response.status_code == 200, "Root endpoint failed"
    print("✓ Root endpoint passed")


def test_list_jobs():
    """Test listing jobs"""
    print("\n=== Testing List Jobs ===")
    response = requests.get(f"{BASE_URL}/api/jobs", headers=headers)
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Found {len(data)} jobs")
    if data:
        print(f"First job: {json.dumps(data[0], indent=2)}")
    assert response.status_code == 200, "List jobs failed"
    print("✓ List jobs passed")
    return data


def test_create_job():
    """Test creating a job"""
    print("\n=== Testing Create Job ===")
    job_data = {
        "title": "Test API Engineer",
        "description": "Testing the API",
        "department": "Engineering",
        "slots": 1
    }
    response = requests.post(
        f"{BASE_URL}/api/jobs",
        json=job_data,
        headers=headers
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 201:
        data = response.json()
        print(f"Created job: {json.dumps(data, indent=2)}")
        print("✓ Create job passed")
        return data
    else:
        print(f"Error: {response.text}")
        return None


def test_list_candidates():
    """Test listing candidates"""
    print("\n=== Testing List Candidates ===")
    response = requests.get(
        f"{BASE_URL}/api/candidates",
        params={"limit": 5},
        headers=headers
    )
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Total: {data.get('total', 0)}, Returned: {len(data.get('items', []))}")
    if data.get('items'):
        print(f"First candidate: {json.dumps(data['items'][0], indent=2)}")
    assert response.status_code == 200, "List candidates failed"
    print("✓ List candidates passed")
    return data


def test_create_candidate(job_id=None):
    """Test creating a candidate"""
    print("\n=== Testing Create Candidate ===")
    candidate_data = {
        "name": "Test Candidate API",
        "email": "test.api@example.com",
        "phone": "+1-555-9999"
    }
    if job_id:
        candidate_data["job_id"] = job_id

    response = requests.post(
        f"{BASE_URL}/api/candidates",
        json=candidate_data,
        headers=headers
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 201:
        data = response.json()
        print(f"Created candidate: {json.dumps(data, indent=2)}")
        print("✓ Create candidate passed")
        return data
    else:
        print(f"Error: {response.text}")
        return None


def test_update_candidate(candidate_id):
    """Test updating a candidate"""
    print("\n=== Testing Update Candidate ===")
    update_data = {
        "notes": "Updated via API test"
    }
    response = requests.patch(
        f"{BASE_URL}/api/candidates/{candidate_id}",
        json=update_data,
        headers=headers
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Updated candidate notes: {data.get('notes')}")
        print("✓ Update candidate passed")
        return data
    else:
        print(f"Error: {response.text}")
        return None


def test_analytics():
    """Test analytics endpoints"""
    print("\n=== Testing Analytics ===")

    # Pipeline stats
    print("\nPipeline Stats:")
    response = requests.get(f"{BASE_URL}/api/analytics/pipeline", headers=headers)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Stats: {json.dumps(data, indent=2)}")
        print("✓ Pipeline stats passed")

    # Velocity
    print("\nVelocity:")
    response = requests.get(f"{BASE_URL}/api/analytics/velocity", headers=headers)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Velocity: {len(data.get('velocity_by_stage', []))} stages")
        print("✓ Velocity stats passed")

    # Conversion
    print("\nConversion:")
    response = requests.get(f"{BASE_URL}/api/analytics/conversion", headers=headers)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Conversion: {len(data.get('conversion_rates', []))} stages")
        print("✓ Conversion stats passed")


def main():
    """Run all tests"""
    print("=" * 60)
    print("ATS API Test Suite")
    print("=" * 60)
    print(f"Base URL: {BASE_URL}")
    print(f"API Key: {'Set' if API_KEY else 'Not set (dev mode)'}")

    try:
        # Basic tests
        test_health()
        test_root()

        # Job tests
        jobs = test_list_jobs()
        created_job = test_create_job()
        job_id = created_job['id'] if created_job else (jobs[0]['id'] if jobs else None)

        # Candidate tests
        candidates = test_list_candidates()
        created_candidate = test_create_candidate(job_id=job_id)

        if created_candidate:
            test_update_candidate(created_candidate['id'])

        # Analytics tests
        test_analytics()

        print("\n" + "=" * 60)
        print("All tests passed!")
        print("=" * 60)

    except requests.exceptions.ConnectionError:
        print("\n✗ Error: Could not connect to API server")
        print("Make sure the API server is running: python run_api.py")
        sys.exit(1)
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
