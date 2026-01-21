# API Authentication & Style Guide

This document defines authentication rules, authorization model, and API design conventions for the Devices & Telemetry API.

All contributors must follow this guide to ensure:

- consistency across services

- backward compatibility

- secure access control

- predictable API behavior for frontend and QA teams
# References
1. [Authentication and Authorization](#1-authentication--authorization)
   - [Authentication Mechanism](#11-authentication-mechanism)
   - [JWT Token Structure](#12-jwt-token-structure)
   - [Obtaining a Test JWT Token](#13-obtaining-a-test-jwt-token)
   - [Using the Token](#14-using-the-token)
   - [Endpoint Authorization Matrix](#15-endpoint-authorization-matrix)
2. [API Style Guide](#2-api-style-guide)
   - [Naming Conventions](#21-naming-conventions)
   - [HTTP Methods and Semantics](#22-http-methods--semantics)
   - [Schema Versioning](#23-schema-versioning)
   - [Pagination](#24-pagination)
   - [Filtering](#25-filtering)
   - [Timestamp Format](#26-timestamp-format)
   - [Idempotency](#27-idempotency)
   - [Error Response Structure](#28-error-response-structure)
   - [HTTP Status Codes](#29-http-status-codes)
3. [Documentation Links](#3-documentation-links)

## 1. Authentication & Authorization
### 1.1 Authentication Mechanism

The API uses JWT Bearer Token authentication.

All protected endpoints must include the following HTTP header:

```http
Authorization: Bearer <JWT_TOKEN>
```

Requests without a valid token will be rejected with 401 Unauthorized.

### 1.2 JWT Token Structure

A valid JWT token contains the following claims:

| Claim   | Description                                                  |
| ------- | ------------------------------------------------------------ |
| `sub`   | Authenticated user or device identifier                      |
| `scope` | Granted permissions (e.g. `devices:read`, `telemetry:write`) |
| `role`  | Actor role: `user`, `admin`, or `device`                     |
| `exp`   | Token expiration timestamp (Unix epoch)                      |

### 1.3 Obtaining a Test JWT Token

For local development and contract testing, a JWT token can be obtained via the authentication endpoint.

**Request**
```http
POST /api/auth/login
Content-Type: application/json
```
```json
{
  "username": "test_user",
  "password": "password"
}
```
**Response**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```
Access token will automatically expire in 60 minutes.

### 1.4 Using the Token
```http
GET /api/devices/
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```
### 1.5 Endpoint Authorization Matrix
**Devices API**
| Endpoint             | Method | Required Scope   | Required Role |
| -------------------- | ------ | ---------------- | ------------- |
| `/api/devices/`      | GET    | `devices:read`   | user          |
| `/api/devices/`      | POST   | `devices:write`  | admin         |
| `/api/devices/{id}/` | GET    | `devices:read`   | user          |
| `/api/devices/{id}/` | PUT    | `devices:write`  | user/admin    |
| `/api/devices/{id}/` | PATCH  | `devices:write`  | user/admin    |
| `/api/devices/{id}/` | DELETE | `devices:delete` | user/admin    |

**Telemetry API**
| Endpoint               | Method | Required Scope     | Required Role  |
| ---------------------- | ------ | ------------------ | -------------- |
| `/api/telemetry/`      | GET    | `telemetry:read`   | user           |
| `/api/telemetry/`      | POST   | `telemetry:write`  | device / admin |
| `/api/telemetry/{id}/` | GET    | `telemetry:read`   | user           |
| `/api/telemetry/{id}/` | PUT    | `telemetry:write`  | admin          |
| `/api/telemetry/{id}/` | PATCH  | `telemetry:write`  | admin          |
| `/api/telemetry/{id}/` | DELETE | `telemetry:delete` | admin          |

## 2. API Style Guide
### 2.1 Naming Conventions
**URLs**
- lowercase
- plural nouns
- trailing slash required

**Valid**:
```
/api/devices/
/api/telemetry/
```

**Invalid**:
```http
/api/Devices/
/api/device
```
**JSON Fields**
- snake_case
- descriptive and explicit names
```json
{
  "serial_id": "ABC123",
  "created_at": "2026-01-20T12:00:00Z"
}
```
### 2.2 HTTP Methods & Semantics
| Method | Usage                       |
| ------ | --------------------------- |
| GET    | Retrieve resources          |
| POST   | Create a resource           |
| PUT    | Fully replace a resource    |
| PATCH  | Partially update a resource |
| DELETE | Remove a resource           |


All endpoints follow RESTful semantics.

### 2.3 Schema Versioning

The API uses payload-based schema versioning.
```json
{
  "schema_version": "1.0",
  "device": {
    "serial_id": "ABC123",
    "name": "Sensor"
  }
}
```
**Backward-compatible changes:**
- adding optional fields
- extending enums
- relaxing validation rules

**Breaking changes:**
- removing fields
- changing field meaning or type

Breaking changes require a new schema_version.
### 2.4 Pagination

The API uses offset-based pagination.

**Request**
```http
GET /api/devices/?limit=5&offset=0
```

**Response**
```json
{
  "total": 12,
  "limit": 5,
  "offset": 0,
  "items": []
}
```
| Field    | Description               |
| -------- | ------------------------- |
| `total`  | Total number of records   |
| `limit`  | Page size                 |
| `offset` | Number of skipped records |
| `items`  | Result set                |
### 2.5 Filtering

Filtering is performed via query parameters.

Required filters must be explicitly provided.
```http
GET /api/telemetry/?device_id=42&limit=5
```

### 2.6 Timestamp Format

All timestamps must be returned in ISO 8601 format (UTC).
```json
"created_at": "2026-01-20T12:00:00Z"
```
### 2.7 Idempotency

```PUT``` and ```DELETE``` requests are idempotent by definition

```POST``` requests may support an optional Idempotency-Key header
```http
POST /api/devices/
Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000
```
### 2.8 Error Response Structure

All errors follow a unified response format:
```json
{
  "code": 404,
  "message": "Resource not found"
}
```
### 2.9 HTTP Status Codes
| Status Code | Meaning      |
| ----------- | ------------ |
| 200         | OK           |
| 201         | Created      |
| 204         | No Content   |
| 400         | Bad Request  |
| 401         | Unauthorized |
| 403         | Forbidden    |
| 404         | Not Found    |
## 3. Documentation Links

This document must be linked from the main README.md.

#### Documentation: ####

- [API Authentication & Style Guide](#api-authentication--style-guide)
- [OpenAPI Specification](api.yaml) (`docs/api.yaml`)
- [Postman Collection](postman_collection.json) (`docs/postman_collection.json`)
