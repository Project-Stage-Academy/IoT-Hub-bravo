# JWT Authentication Plan

This document describes the JWT-based authentication and authorization design for the IoT Hub MVP. It defines token issuance, validation, refresh flow, required claims, and endpoint access control.

## Overview

The API uses JSON Web Tokens (JWT) for stateless authentication. All protected endpoints require a valid JWT token in the `Authorization` header. Tokens are issued after successful user authentication and contain claims that define user identity, role, and granted permissions (scopes).

## Token Structure

### JWT Claims

A valid JWT token contains the following standard and custom claims:

| Claim | Type | Description | Example |
|-------|------|-------------|---------|
| `sub` | string | Subject - authenticated user ID | `"1"` |
| `role` | string | User role: `admin` or `client` | `"admin"` |
| `scope` | string | Comma-separated list of granted permissions | `"devices:read,telemetry:write"` |
| `exp` | integer | Token expiration timestamp (Unix epoch) | `1737561600` |
| `iat` | integer | Token issued at timestamp (Unix epoch) | `1737558000` |
| `jti` | string | JWT ID - unique token identifier | `"550e8400-e29b-41d4-a716-446655440000"` |

### Token Format

```json
{
  "sub": "1",
  "role": "admin",
  "scope": "devices:read,devices:write,telemetry:read,telemetry:write",
  "exp": 1737561600,
  "iat": 1737558000,
  "jti": "550e8400-e29b-41d4-a716-446655440000"
}
```

## Token Lifetime

### Development Environment
- **Access Token**: 60 minutes
- **Refresh Token**: 7 days (if implemented)

### Staging/Production Environment
- **Access Token**: 15 minutes
- **Refresh Token**: 24 hours (if implemented)

Token lifetime is configurable via Django settings (see Configuration section).

## Token Issuance Flow

### 1. Login Endpoint

**Endpoint**: `POST /api/auth/login`

**Request**:
```json
{
  "username": "testuser",
  "password": "password123"
}
```

**Response** (200 OK):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

**Error Response** (401 Unauthorized):
```json
{
  "code": 401,
  "message": "Invalid credentials"
}
```

### 2. Token Generation Process

1. Validate user credentials (username/password)
2. Retrieve user from database
3. Check if user is active (`is_active=True`)
4. Determine user role (`admin` or `client`)
5. Generate scopes based on role (see Scopes section)
6. Create JWT payload with claims
7. Sign token using `SECRET_KEY` (HS256 algorithm)
8. Return token in response

### 3. Scope Assignment by Role

**Admin Role**:
- `devices:read`
- `devices:write`
- `devices:delete`
- `telemetry:read`
- `telemetry:write`
- `telemetry:delete`
- `admin:access`

**Client Role**:
- `devices:read`
- `telemetry:read`
- `telemetry:write` (for their own devices only)

## Token Refresh Flow

### Refresh Endpoint

**Endpoint**: `POST /api/auth/refresh`

**Request**:
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response** (200 OK):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

**Note**: Refresh token implementation is optional for MVP. If not implemented, users must re-authenticate when access token expires.

## Token Validation

### Middleware Process

1. Extract `Authorization` header from request
2. Parse `Bearer <token>` format
3. Decode and validate JWT signature using `SECRET_KEY`
4. Check token expiration (`exp` claim)
5. Verify required claims (`sub`, `role`, `scope`)
6. Attach user context to request object
7. Continue to view or return 401 if validation fails

### Validation Errors

| HTTP Status | Error Code | Description |
|-------------|------------|-------------|
| 401 | `token_missing` | Authorization header not provided |
| 401 | `token_invalid` | Token format is invalid |
| 401 | `token_expired` | Token has expired |
| 401 | `token_signature_invalid` | Token signature verification failed |
| 403 | `insufficient_scope` | Token lacks required scope |

## Endpoint Authorization Matrix

### Devices API

| Endpoint | Method | Required Scope | Required Role | Notes |
|----------|--------|----------------|---------------|-------|
| `/api/devices/` | GET | `devices:read` | `client`, `admin` | List all devices (clients see only their own) |
| `/api/devices/` | POST | `devices:write` | `admin` | Create new device |
| `/api/devices/{id}/` | GET | `devices:read` | `client`, `admin` | Get device details |
| `/api/devices/{id}/` | PUT | `devices:write` | `admin` | Full update |
| `/api/devices/{id}/` | PATCH | `devices:write` | `admin` | Partial update |
| `/api/devices/{id}/` | DELETE | `devices:delete` | `admin` | Delete device |

### Telemetry API

| Endpoint | Method | Required Scope | Required Role | Notes |
|----------|--------|----------------|---------------|-------|
| `/api/telemetry/` | GET | `telemetry:read` | `client`, `admin` | List telemetry (clients see only their devices) |
| `/api/telemetry/` | POST | `telemetry:write` | `client`, `admin` | Create telemetry record |
| `/api/telemetry/{id}/` | GET | `telemetry:read` | `client`, `admin` | Get telemetry details |
| `/api/telemetry/{id}/` | PUT | `telemetry:write` | `admin` | Full update |
| `/api/telemetry/{id}/` | PATCH | `telemetry:write` | `admin` | Partial update |
| `/api/telemetry/{id}/` | DELETE | `telemetry:delete` | `admin` | Delete telemetry |

### Authentication Endpoints

| Endpoint | Method | Authentication Required | Notes |
|----------|--------|------------------------|-------|
| `/api/auth/login` | POST | No | Public endpoint |
| `/api/auth/refresh` | POST | No | Public endpoint (validates refresh token) |

### Admin Interface

| Endpoint | Method | Required Scope | Required Role | Notes |
|----------|--------|----------------|---------------|-------|
| `/admin/` | GET | `admin:access` | `admin` | Django admin interface |
| `/admin/*` | All | `admin:access` | `admin` | All admin routes |

## Django Configuration

### Required Libraries

Add to `backend/requirements.txt`:
```
PyJWT==2.8.0
cryptography==42.0.0  # Optional, for RS256 if needed
```

### Settings Configuration

Add to `backend/conf/settings.py`:

```python
import os
from datetime import timedelta
from decouple import config

# JWT Configuration
JWT_SECRET_KEY = config('JWT_SECRET_KEY', default=SECRET_KEY)
JWT_ALGORITHM = config('JWT_ALGORITHM', default='HS256')
JWT_ACCESS_TOKEN_LIFETIME = timedelta(
    minutes=config('JWT_ACCESS_TOKEN_LIFETIME_MINUTES', default=60, cast=int)
)
JWT_REFRESH_TOKEN_LIFETIME = timedelta(
    days=config('JWT_REFRESH_TOKEN_LIFETIME_DAYS', default=7, cast=int)
)

# Token lifetime by environment
if DEBUG:
    JWT_ACCESS_TOKEN_LIFETIME = timedelta(minutes=60)
else:
    JWT_ACCESS_TOKEN_LIFETIME = timedelta(minutes=15)

# Scope definitions
JWT_SCOPES = {
    'admin': [
        'devices:read',
        'devices:write',
        'devices:delete',
        'telemetry:read',
        'telemetry:write',
        'telemetry:delete',
        'admin:access',
    ],
    'client': [
        'devices:read',
        'telemetry:read',
        'telemetry:write',
    ],
}

# JWT Authentication Middleware
MIDDLEWARE = [
    # ... existing middleware ...
    'apps.users.middleware.jwt_auth.JWTAuthenticationMiddleware',
    # ... rest of middleware ...
]
```

### Environment Variables

Add to `.env` file:

```env
# JWT Configuration
# Use a different key from SECRET_KEY for additional security
JWT_SECRET_KEY=your-jwt-secret-key-here-min-32-chars
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_LIFETIME_MINUTES=60
JWT_REFRESH_TOKEN_LIFETIME_DAYS=7
```

**Security Note**: `JWT_SECRET_KEY` should be different from `SECRET_KEY` and never committed to version control.

## Implementation Example

### Token Issuance (Login View)

```python
import jwt
from datetime import datetime, timedelta
from django.conf import settings
from django.contrib.auth import authenticate
from rest_framework.response import Response
from rest_framework import status

def login_view(request):
    username = request.data.get('username')
    password = request.data.get('password')
    
    user = authenticate(username=username, password=password)
    if not user or not user.is_active:
        return Response(
            {'code': 401, 'message': 'Invalid credentials'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    # Generate scopes based on role
    scopes = settings.JWT_SCOPES.get(user.role, [])
    
    # Create token payload
    now = datetime.utcnow()
    payload = {
        'sub': str(user.id),
        'role': user.role,
        'scope': ','.join(scopes),
        'exp': now + settings.JWT_ACCESS_TOKEN_LIFETIME,
        'iat': now,
        'jti': str(uuid.uuid4()),
    }
    
    # Sign token
    token = jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    
    return Response({
        'access_token': token,
        'token_type': 'bearer',
        'expires_in': int(settings.JWT_ACCESS_TOKEN_LIFETIME.total_seconds())
    })
```

### Token Validation (Middleware)

```python
import jwt
from django.conf import settings
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin

class JWTAuthenticationMiddleware(MiddlewareMixin):
    """Validates JWT tokens and attaches user context to request."""
    
    # Public endpoints that don't require authentication
    PUBLIC_PATHS = [
        '/api/auth/login',
        '/api/auth/refresh',
        '/admin/login',
    ]
    
    def process_request(self, request):
        # Skip authentication for public paths
        if any(request.path.startswith(path) for path in self.PUBLIC_PATHS):
            return None
        
        # Extract token from Authorization header
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if not auth_header.startswith('Bearer '):
            return JsonResponse(
                {'code': 401, 'message': 'Token missing'},
                status=401
            )
        
        token = auth_header.split(' ')[1]
        
        try:
            # Decode and validate token
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )
            
            # Attach user info to request
            request.jwt_payload = payload
            request.user_id = payload['sub']
            request.user_role = payload['role']
            request.user_scopes = payload['scope'].split(',')
            
        except jwt.ExpiredSignatureError:
            return JsonResponse(
                {'code': 401, 'message': 'Token expired'},
                status=401
            )
        except jwt.InvalidTokenError:
            return JsonResponse(
                {'code': 401, 'message': 'Invalid token'},
                status=401
            )
        
        return None
```

## Security Considerations

### Token Storage
- **Client-side**: Store tokens in memory or secure HTTP-only cookies (preferred)
- **Never**: Store tokens in localStorage (XSS risk) or sessionStorage

### Token Revocation
- MVP does not implement token blacklisting
- To revoke a token, rotate `JWT_SECRET_KEY` (invalidates all tokens)
- For production, implement token blacklist using Redis or database

### Secret Key Management
- Use different `JWT_SECRET_KEY` from `SECRET_KEY`
- Rotate keys periodically (e.g., every 90 days)
- Store keys in environment variables, never in code
- Use strong, randomly generated keys (minimum 32 characters)

### Best Practices
1. Always use HTTPS in staging/production
2. Set appropriate token lifetimes (shorter for production)
3. Validate all claims, not just expiration
4. Log authentication failures for security monitoring
5. Implement rate limiting on login endpoints

## References

- [Security Plan](./security_plan.md) - Overall security strategy
- [API Guide](./api-guide.md) - API authentication usage
- [JWT.io](https://jwt.io/) - JWT specification and debugger
- [PyJWT Documentation](https://pyjwt.readthedocs.io/) - Python JWT library

## Document Maintenance

**Last Updated**: 2026-01-22  
**Next Review**: 2026-04-22

This document should be updated when:
- New endpoints are added
- Role or scope definitions change
- Token lifetime policies are modified
- Security requirements evolve



