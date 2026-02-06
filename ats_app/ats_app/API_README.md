# ATS REST API Documentation

A FastAPI-based REST API for the Applicant Tracking System that runs alongside the Streamlit application.

## Features

- RESTful API endpoints for candidates, jobs, interviews, and analytics
- Optional API key authentication
- CORS support for cross-origin requests
- Automatic API documentation (Swagger/OpenAPI)
- Pagination support for list endpoints
- Structured error responses

## Quick Start

### 1. Install Dependencies

```bash
pip install fastapi uvicorn pydantic
```

### 2. Run the API Server

```bash
# Default: http://0.0.0.0:8000
python run_api.py

# Custom host/port
API_HOST=127.0.0.1 API_PORT=8080 python run_api.py
```

### 3. Access API Documentation

Open your browser to:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Authentication

### API Key Authentication

Set the `API_KEY` environment variable to enable authentication:

```bash
API_KEY=your-secret-key-here python run_api.py
```

Include the API key in requests:

```bash
curl -H "X-API-Key: your-secret-key-here" http://localhost:8000/api/candidates
```

### Development Mode

If `API_KEY` is not set, authentication is disabled (dev mode).

## API Endpoints

### Health Check

**GET /api/health**

Check API and database health.

```bash
curl http://localhost:8000/api/health
```

Response:
```json
{
  "status": "ok",
  "timestamp": "2025-01-15T10:00:00",
  "database": "healthy"
}
```

---

### Candidates

#### List Candidates

**GET /api/candidates**

Query Parameters:
- `status` (string): Filter by status (default: "Active")
- `job_id` (integer): Filter by job ID
- `stage` (string): Filter by stage
- `limit` (integer): Number of results (1-500, default: 50)
- `offset` (integer): Pagination offset (default: 0)

```bash
curl -H "X-API-Key: your-key" \
  "http://localhost:8000/api/candidates?status=Active&limit=10"
```

Response:
```json
{
  "items": [...],
  "total": 42,
  "limit": 10,
  "offset": 0
}
```

#### Get Candidate

**GET /api/candidates/{candidate_id}**

```bash
curl -H "X-API-Key: your-key" \
  http://localhost:8000/api/candidates/123
```

#### Create Candidate

**POST /api/candidates**

Request Body:
```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "phone": "+1-555-0100",
  "job_id": 1,
  "vendor_id": 2,
  "resume_text": "Resume content..."
}
```

```bash
curl -X POST -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{"name":"John Doe","email":"john@example.com"}' \
  http://localhost:8000/api/candidates
```

#### Update Candidate

**PATCH /api/candidates/{candidate_id}**

Request Body (all fields optional):
```json
{
  "name": "Jane Doe",
  "email": "jane@example.com",
  "phone": "+1-555-0200",
  "current_stage": "Phone Screen",
  "notes": "Great candidate"
}
```

#### Advance Candidate

**POST /api/candidates/{candidate_id}/advance?new_stage=Phone%20Screen**

```bash
curl -X POST -H "X-API-Key: your-key" \
  "http://localhost:8000/api/candidates/123/advance?new_stage=Phone%20Screen"
```

#### Reject Candidate

**POST /api/candidates/{candidate_id}/reject**

```bash
curl -X POST -H "X-API-Key: your-key" \
  http://localhost:8000/api/candidates/123/reject
```

---

### Jobs

#### List Jobs

**GET /api/jobs**

Query Parameters:
- `status` (string): Filter by status (e.g., "Open", "Closed")

```bash
curl -H "X-API-Key: your-key" \
  "http://localhost:8000/api/jobs?status=Open"
```

#### Get Job

**GET /api/jobs/{job_id}**

Returns job details with candidate statistics.

```bash
curl -H "X-API-Key: your-key" \
  http://localhost:8000/api/jobs/1
```

Response includes:
```json
{
  "id": 1,
  "title": "Senior Engineer",
  "total_candidates": 25,
  "active_candidates": 15,
  "hired_count": 2,
  "remaining_slots": 3
}
```

#### Create Job

**POST /api/jobs**

Request Body:
```json
{
  "title": "Senior Software Engineer",
  "description": "We are looking for...",
  "requirements": "5+ years experience...",
  "department": "Engineering",
  "slots": 3
}
```

#### Update Job

**PATCH /api/jobs/{job_id}**

Request Body (all fields optional):
```json
{
  "title": "Lead Software Engineer",
  "status": "Closed",
  "slots": 5
}
```

---

### Interviews

#### List Interviews

**GET /api/interviews**

Query Parameters:
- `upcoming_only` (boolean): Only return upcoming interviews (default: false)

```bash
curl -H "X-API-Key: your-key" \
  "http://localhost:8000/api/interviews?upcoming_only=true"
```

#### Schedule Interview

**POST /api/interviews**

Request Body:
```json
{
  "candidate_id": 123,
  "stage": "Technical Interview",
  "scheduled_time": "2025-01-20T14:00:00Z",
  "interviewer_email": "interviewer@company.com",
  "interviewer_name": "Alice Smith",
  "location": "Conference Room A",
  "meeting_link": "https://zoom.us/j/123456789"
}
```

---

### Analytics

#### Pipeline Statistics

**GET /api/analytics/pipeline**

Query Parameters:
- `job_id` (integer): Filter by job ID (optional)

Returns candidate counts by stage.

```bash
curl -H "X-API-Key: your-key" \
  http://localhost:8000/api/analytics/pipeline
```

Response:
```json
{
  "job_id": null,
  "stats_by_stage": {
    "Resume Screen": 50,
    "Phone Screen": 25,
    "Technical Interview": 10,
    "Offer": 3
  },
  "total_active": 88
}
```

#### Pipeline Velocity

**GET /api/analytics/velocity**

Query Parameters:
- `job_id` (integer): Filter by job ID (optional)

Returns average days spent in each stage.

```bash
curl -H "X-API-Key: your-key" \
  http://localhost:8000/api/analytics/velocity
```

Response:
```json
{
  "job_id": null,
  "velocity_by_stage": [
    {
      "stage": "Resume Screen",
      "avg_days": 2.5,
      "min_days": 1.0,
      "max_days": 7.0,
      "candidate_count": 50
    }
  ]
}
```

#### Stage Conversion Rates

**GET /api/analytics/conversion**

Query Parameters:
- `job_id` (integer): Filter by job ID (optional)

Returns conversion rates between stages.

```bash
curl -H "X-API-Key: your-key" \
  http://localhost:8000/api/analytics/conversion
```

Response:
```json
{
  "job_id": null,
  "conversion_rates": [
    {
      "from_stage": "Resume Screen",
      "to_stage": "Phone Screen",
      "total_entered": 100,
      "advanced": 50,
      "rejected": 30,
      "still_in_stage": 20,
      "conversion_rate": 50.0
    }
  ]
}
```

---

## Error Responses

All errors follow a consistent format:

```json
{
  "detail": "Error message here"
}
```

### Status Codes

- **200 OK**: Successful GET/PATCH request
- **201 Created**: Successful POST request
- **400 Bad Request**: Invalid input data
- **401 Unauthorized**: Missing or invalid API key
- **404 Not Found**: Resource not found
- **422 Unprocessable Entity**: Validation error
- **500 Internal Server Error**: Server error

## Configuration

Environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `API_KEY` | API key for authentication (empty = dev mode) | `""` |
| `API_HOST` | Host to bind to | `0.0.0.0` |
| `API_PORT` | Port to listen on | `8000` |
| `DB_PATH` | Database file path | `ats_data.db` |
| `DATABASE_URL` | PostgreSQL URL (optional) | `""` |

## Running Alongside Streamlit

You can run both the Streamlit app and the FastAPI server simultaneously:

Terminal 1 (Streamlit):
```bash
streamlit run app.py
```

Terminal 2 (API):
```bash
python run_api.py
```

Both applications share the same database.

## Integration Examples

### Python

```python
import requests

API_KEY = "your-key-here"
BASE_URL = "http://localhost:8000"

headers = {"X-API-Key": API_KEY}

# List candidates
response = requests.get(f"{BASE_URL}/api/candidates", headers=headers)
candidates = response.json()

# Create candidate
new_candidate = {
    "name": "John Doe",
    "email": "john@example.com",
    "job_id": 1
}
response = requests.post(
    f"{BASE_URL}/api/candidates",
    json=new_candidate,
    headers=headers
)
created = response.json()
```

### JavaScript/Node.js

```javascript
const API_KEY = 'your-key-here';
const BASE_URL = 'http://localhost:8000';

const headers = {
  'X-API-Key': API_KEY,
  'Content-Type': 'application/json'
};

// List candidates
fetch(`${BASE_URL}/api/candidates`, { headers })
  .then(res => res.json())
  .then(data => console.log(data));

// Create candidate
fetch(`${BASE_URL}/api/candidates`, {
  method: 'POST',
  headers,
  body: JSON.stringify({
    name: 'John Doe',
    email: 'john@example.com',
    job_id: 1
  })
})
  .then(res => res.json())
  .then(data => console.log(data));
```

### cURL Examples

```bash
# Set variables
API_KEY="your-key-here"
BASE_URL="http://localhost:8000"

# List candidates
curl -H "X-API-Key: $API_KEY" "$BASE_URL/api/candidates"

# Get candidate
curl -H "X-API-Key: $API_KEY" "$BASE_URL/api/candidates/123"

# Create candidate
curl -X POST -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name":"John Doe","email":"john@example.com","job_id":1}' \
  "$BASE_URL/api/candidates"

# Update candidate
curl -X PATCH -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"notes":"Great candidate"}' \
  "$BASE_URL/api/candidates/123"

# Advance candidate
curl -X POST -H "X-API-Key: $API_KEY" \
  "$BASE_URL/api/candidates/123/advance?new_stage=Phone%20Screen"

# Get analytics
curl -H "X-API-Key: $API_KEY" "$BASE_URL/api/analytics/pipeline"
```

## Testing

### Manual Testing

Use the interactive API documentation at `/docs`:

1. Navigate to http://localhost:8000/docs
2. Click "Authorize" and enter your API key
3. Try out endpoints interactively

### Automated Testing

Create a test script:

```python
import requests
import pytest

BASE_URL = "http://localhost:8000"
API_KEY = "your-key-here"
headers = {"X-API-Key": API_KEY}

def test_health():
    response = requests.get(f"{BASE_URL}/api/health")
    assert response.status_code == 200
    assert response.json()["status"] in ["ok", "degraded"]

def test_create_and_get_candidate():
    # Create
    candidate = {"name": "Test User", "email": "test@example.com"}
    response = requests.post(
        f"{BASE_URL}/api/candidates",
        json=candidate,
        headers=headers
    )
    assert response.status_code == 201
    created = response.json()
    candidate_id = created["id"]

    # Get
    response = requests.get(
        f"{BASE_URL}/api/candidates/{candidate_id}",
        headers=headers
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Test User"
```

## Deployment

### Production Considerations

1. **Set API Key**: Always use a strong API key in production
2. **Configure CORS**: Update `allow_origins` in `api.py` to whitelist specific domains
3. **Use HTTPS**: Deploy behind a reverse proxy (nginx, Apache) with SSL
4. **Rate Limiting**: Consider adding rate limiting middleware
5. **Monitoring**: Add logging and monitoring (e.g., Sentry, DataDog)

### Docker Deployment

Create a `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "run_api.py"]
```

Build and run:

```bash
docker build -t ats-api .
docker run -p 8000:8000 -e API_KEY=your-key ats-api
```

## Support

For issues or questions, refer to the main ATS application documentation or check the Swagger documentation at `/docs`.
