# Testing Best Practices Skill

## Test Pyramid
```
         /\
        /  \      E2E (10%)
       /----\     - Complete user workflows
      /      \    - Real browser, production-like
     /--------\   
    /  Integ   \  Integration (20%)
   /   (20%)    \ - Component interactions
  /--------------\- Real database (Testcontainers)
 /     Unit       \
/      (70%)       \ Unit (70%)
--------------------  - Single function/component
                      - Fast, isolated
```

## Python Testing (pytest)

### Project Structure
```
tests/
├── conftest.py          # Shared fixtures
├── unit/
│   ├── test_services.py
│   └── test_utils.py
├── integration/
│   ├── conftest.py      # DB fixtures
│   └── test_api.py
└── e2e/
    └── test_workflows.py
```

### Fixtures (conftest.py)
```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from testcontainers.postgres import PostgresContainer

from src.models.base import Base
from src.main import create_app
from src.api.deps import get_db

# Real database for integration tests
@pytest.fixture(scope="session")
def postgres():
    with PostgresContainer("postgres:15") as pg:
        yield pg

@pytest.fixture(scope="session")
def engine(postgres):
    return create_engine(postgres.get_connection_url())

@pytest.fixture(scope="function")
def db(engine):
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client(db):
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db
    from fastapi.testclient import TestClient
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

# Factory fixtures
@pytest.fixture
def user_factory(db):
    def create_user(**kwargs):
        defaults = {
            "name": "Test User",
            "email": f"test_{uuid4().hex[:8]}@example.com",
        }
        defaults.update(kwargs)
        user = User(**defaults)
        db.add(user)
        db.commit()
        return user
    return create_user
```

### Unit Tests
```python
# tests/unit/test_services.py
import pytest
from unittest.mock import Mock, patch

from src.services.user import UserService

class TestUserService:
    def test_validate_email_valid(self):
        assert UserService.validate_email("test@example.com") is True
    
    def test_validate_email_invalid(self):
        assert UserService.validate_email("invalid") is False
    
    @patch('src.services.user.db')
    def test_get_by_id_found(self, mock_db):
        mock_user = Mock(id=1, name="Test")
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        result = UserService(mock_db).get_by_id(1)
        
        assert result.id == 1
        assert result.name == "Test"
    
    @patch('src.services.user.db')
    def test_get_by_id_not_found(self, mock_db):
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        result = UserService(mock_db).get_by_id(999)
        
        assert result is None
```

### Integration Tests
```python
# tests/integration/test_api.py
import pytest

class TestUserAPI:
    def test_create_user(self, client):
        response = client.post("/api/users/", json={
            "name": "New User",
            "email": "new@example.com",
            "password": "SecurePass123"
        })
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New User"
        assert data["email"] == "new@example.com"
        assert "id" in data
        assert "password" not in data
    
    def test_create_user_duplicate_email(self, client, user_factory):
        existing = user_factory(email="taken@example.com")
        
        response = client.post("/api/users/", json={
            "name": "Another User",
            "email": "taken@example.com",
            "password": "SecurePass123"
        })
        
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]
    
    def test_get_user(self, client, user_factory):
        user = user_factory(name="Test User")
        
        response = client.get(f"/api/users/{user.id}")
        
        assert response.status_code == 200
        assert response.json()["name"] == "Test User"
    
    def test_get_user_not_found(self, client):
        response = client.get("/api/users/99999")
        
        assert response.status_code == 404
```

## TypeScript Testing (Vitest)

### Project Structure
```
tests/
├── setup.ts             # Global setup
├── utils.tsx            # Test utilities
├── unit/
│   └── utils.test.ts
├── components/
│   └── Button.test.tsx
└── integration/
    └── api.test.ts
```

### Setup
```typescript
// tests/setup.ts
import { afterEach } from 'vitest'
import { cleanup } from '@testing-library/react'
import '@testing-library/jest-dom/vitest'

afterEach(() => {
  cleanup()
})
```

### Component Tests
```typescript
// tests/components/UserProfile.test.tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { UserProfile } from '@/components/UserProfile'

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } }
  })
  return ({ children }) => (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  )
}

describe('UserProfile', () => {
  it('displays user information', async () => {
    render(<UserProfile userId="123" />, { wrapper: createWrapper() })
    
    expect(screen.getByRole('status')).toHaveTextContent('Loading')
    
    await waitFor(() => {
      expect(screen.getByRole('heading')).toHaveTextContent('John Doe')
    })
    
    expect(screen.getByText('john@example.com')).toBeInTheDocument()
  })
  
  it('allows editing name', async () => {
    render(<UserProfile userId="123" />, { wrapper: createWrapper() })
    
    await screen.findByRole('heading')
    
    fireEvent.click(screen.getByRole('button', { name: /edit/i }))
    
    const input = screen.getByRole('textbox', { name: /name/i })
    fireEvent.change(input, { target: { value: 'Jane Doe' } })
    fireEvent.click(screen.getByRole('button', { name: /save/i }))
    
    await waitFor(() => {
      expect(screen.getByRole('heading')).toHaveTextContent('Jane Doe')
    })
  })
  
  it('shows error state', async () => {
    // Mock API failure
    vi.spyOn(global, 'fetch').mockRejectedValueOnce(new Error('Network error'))
    
    render(<UserProfile userId="123" />, { wrapper: createWrapper() })
    
    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('Failed to load')
    })
  })
})
```

### API Mocking (MSW)
```typescript
// tests/mocks/handlers.ts
import { http, HttpResponse } from 'msw'

export const handlers = [
  http.get('/api/users/:id', ({ params }) => {
    return HttpResponse.json({
      id: params.id,
      name: 'John Doe',
      email: 'john@example.com',
    })
  }),
  
  http.patch('/api/users/:id', async ({ params, request }) => {
    const body = await request.json()
    return HttpResponse.json({
      id: params.id,
      ...body,
    })
  }),
]

// tests/setup.ts
import { setupServer } from 'msw/node'
import { handlers } from './mocks/handlers'

export const server = setupServer(...handlers)

beforeAll(() => server.listen())
afterEach(() => server.resetHandlers())
afterAll(() => server.close())
```

## Test Patterns

### AAA Pattern
```python
def test_user_creation():
    # Arrange
    service = UserService(db)
    data = {"name": "Test", "email": "test@example.com"}
    
    # Act
    result = service.create(data)
    
    # Assert
    assert result.id is not None
    assert result.name == "Test"
```

### Given-When-Then
```python
def test_user_login():
    # Given: A registered user
    user = user_factory(email="user@example.com", password="secret")
    
    # When: They login with correct credentials
    response = client.post("/auth/login", json={
        "email": "user@example.com",
        "password": "secret"
    })
    
    # Then: They receive a valid token
    assert response.status_code == 200
    assert "access_token" in response.json()
```

## Anti-Patterns

### ❌ Testing Implementation Details
```python
# BAD: Testing internal state
def test_bad():
    component._internal_state = "value"
    assert component._internal_state == "value"

# GOOD: Testing behavior
def test_good():
    component.set_value("value")
    assert component.get_display() == "Value: value"
```

### ❌ Mocking Everything
```python
# BAD: Mocking database in integration test
@patch('src.db.session')
def test_bad(mock_db):
    ...

# GOOD: Using real database
def test_good(db):  # Real Testcontainers DB
    ...
```

### ❌ Brittle Selectors
```typescript
// BAD
screen.getByClassName('btn-primary')

// GOOD
screen.getByRole('button', { name: /submit/i })
```

## Commands
```bash
# Python
pytest                          # Run all
pytest -v                       # Verbose
pytest -k "test_user"          # Filter by name
pytest --cov=src               # Coverage
pytest -x                       # Stop on first failure

# TypeScript
npm test                        # Run all
npm run test:watch             # Watch mode
npm run test:coverage          # Coverage
npm run test:ui                # Vitest UI
```
