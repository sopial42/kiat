# API Conventions: REST Design & Error Handling

Standards for building HTTP APIs with consistent contracts, error codes, and response formats.

---

## REST Principles

### Naming Conventions

**Resources**: Plural nouns, lowercase, hyphenated
```
GET    /users              # List all users
POST   /users              # Create user
GET    /users/:id          # Get one user
PATCH  /users/:id          # Update user
DELETE /users/:id          # Delete user

GET    /users/:id/orders   # List user's orders
POST   /users/:id/orders   # Create order for user
```

**No verbs in URLs**:
```
❌ GET  /users/:id/getOrders
❌ POST /users/:id/createOrder
✅ GET  /users/:id/orders
✅ POST /users/:id/orders
```

### HTTP Methods

| Method | Purpose | Request Body | Response Body |
|---|---|---|---|
| GET | Read resource | No | Resource JSON |
| POST | Create resource | Required | Created resource + 201 |
| PATCH | Partial update | Required | Updated resource + 200 |
| DELETE | Delete resource | No | Empty + 204 |
| PUT | Full replace | Required | Replaced resource + 200 |

**PATCH vs PUT**:
- **PATCH**: Partial update (only send changed fields)
  ```json
  PATCH /users/123
  { "name": "New Name" }
  → Returns: { "id": "123", "email": "...", "name": "New Name" }
  ```

- **PUT**: Full replace (send entire object)
  ```json
  PUT /users/123
  { "id": "123", "email": "new@example.com", "name": "Name" }
  → Returns: entire user object
  ```

---

## Request/Response Format

### Standard Response Envelope

**Success (2xx)**:
```json
{
  "data": { /* resource or array of resources */ },
  "meta": { /* pagination, timestamps, etc */ }
}
```

**Error (4xx, 5xx)**:
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error",
    "details": { /* optional: field-level errors */ }
  }
}
```

### Examples

**GET /users/:id (200 OK)**:
```json
{
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "name": "Alice",
    "createdAt": "2026-01-15T10:30:00Z"
  }
}
```

**POST /users (201 Created)**:
```json
{
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440001",
    "email": "newuser@example.com",
    "name": "Bob",
    "createdAt": "2026-01-15T10:31:00Z"
  }
}
```

**GET /users (200 OK with pagination)**:
```json
{
  "data": [
    { "id": "...", "email": "user1@example.com", ... },
    { "id": "...", "email": "user2@example.com", ... }
  ],
  "meta": {
    "total": 100,
    "page": 1,
    "pageSize": 20,
    "hasMore": true
  }
}
```

**PATCH /users/:id with validation error (400 Bad Request)**:
```json
{
  "error": {
    "code": "INVALID_INPUT",
    "message": "validation failed",
    "details": {
      "name": "name must be at least 2 characters",
      "email": "email format is invalid"
    }
  }
}
```

---

## Standard Error Codes

| Code | HTTP | Meaning | Example |
|---|---|---|---|
| INVALID_INPUT | 400 | Input validation failed | Missing required field, format error |
| INVALID_EMAIL | 400 | Email format invalid | "notanemail" |
| INVALID_NAME | 400 | Name validation failed | Too short, invalid characters |
| UNAUTHORIZED | 401 | Missing or invalid authentication | No JWT token, expired token |
| FORBIDDEN | 403 | Authenticated but not allowed | User A reading User B's data (RLS denied) |
| NOT_FOUND | 404 | Resource doesn't exist | GET /users/:id with invalid ID |
| DUPLICATE_EMAIL | 409 | Email already exists | POST /users with existing email |
| CONFLICT | 409 | State conflict (optimistic locking) | PATCH /users/:id with stale updated_at |
| RATE_LIMITED | 429 | Too many requests | Rate limit exceeded |
| INTERNAL_ERROR | 500 | Server error | Unexpected exception, database down |
| SERVICE_UNAVAILABLE | 503 | External service down | Clerk API timeout, S3 unavailable |

---

## Authentication

### JWT Token Format

**Header**:
```
Authorization: Bearer <jwt_token>
```

**Validation**:
- JWT must be valid (signature, expiry)
- If invalid/expired → 401 UNAUTHORIZED
- Middleware: Extract user_id from JWT claims

**Example middleware**:
```go
func AuthMiddleware() gin.HandlerFunc {
    return func(c *gin.Context) {
        token := c.GetHeader("Authorization")
        if token == "" {
            c.JSON(http.StatusUnauthorized, ErrorResponse{
                Code: "UNAUTHORIZED",
                Message: "missing authorization header",
            })
            c.Abort()
            return
        }

        userID, err := VerifyJWT(token)
        if err != nil {
            c.JSON(http.StatusUnauthorized, ErrorResponse{
                Code: "UNAUTHORIZED",
                Message: "invalid or expired token",
            })
            c.Abort()
            return
        }

        c.Set("user_id", userID)
        c.Next()
    }
}
```

---

## Pagination

**Query parameters**:
```
GET /users?page=1&pageSize=20
```

**Response includes**:
```json
{
  "data": [ /* items */ ],
  "meta": {
    "total": 100,
    "page": 1,
    "pageSize": 20,
    "hasMore": true
  }
}
```

**Defaults**:
- `page`: 1 (first page)
- `pageSize`: 20 (items per page)
- Max pageSize: 100 (prevent large queries)

---

## Timestamps

**Format**: ISO 8601 with UTC timezone
```
2026-01-15T10:30:00Z
```

**In responses**: Always include `createdAt` and `updatedAt`
```json
{
  "id": "...",
  "name": "...",
  "createdAt": "2026-01-15T10:30:00Z",
  "updatedAt": "2026-01-15T10:35:00Z"
}
```

---

## Common Patterns

### Filtering

**Query parameters** (depends on resource):
```
GET /users?email=alice@example.com
GET /orders?status=pending
GET /posts?tag=react
```

**Guidelines**:
- Use exact match or simple filters (not complex queries)
- For complex filtering, use dedicated endpoints
- Document supported filters in API spec

### Sorting

**Query parameter**:
```
GET /users?sortBy=name&sortOrder=asc
GET /users?sortBy=createdAt&sortOrder=desc
```

**Allowed values**:
- `sortBy`: Specific field (name, email, createdAt, etc.)
- `sortOrder`: "asc" or "desc"

### Soft Delete

If resource has `deletedAt`:
```
GET /users              # Returns only non-deleted
GET /users?includeDeleted=true  # Includes deleted
DELETE /users/:id       # Sets deletedAt = now()
```

---

## Rate Limiting

**Headers** (if implemented):
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1234567890
```

**When exceeded (429 Too Many Requests)**:
```json
{
  "error": {
    "code": "RATE_LIMITED",
    "message": "too many requests, retry after 60 seconds"
  }
}
```

---

## Versioning

**Option 1: URL path** (recommended for major changes)
```
GET /v1/users
GET /v2/users     # Breaking change
```

**Option 2: Header**
```
Accept: application/vnd.example.v1+json
Accept: application/vnd.example.v2+json
```

**Policy**:
- Introduce new version only for breaking changes
- Support old version for 1-2 releases
- Document deprecation in response headers

---

## Best Practices

### ✅ Do

- Return appropriate HTTP status codes (201 for create, 204 for delete)
- Include `createdAt` and `updatedAt` on every resource
- Validate input before processing
- Use consistent error codes across API
- Document required vs optional fields
- Include trace_id in error responses (for debugging)

### ❌ Don't

- Leak internal error messages to clients
- Return 200 for errors (use 4xx, 5xx)
- Use verbs in URLs (it's a resource API, not RPC)
- Return different formats for same endpoint
- Forget authentication/authorization checks
- Forget to validate file uploads (size, type)

---

## Example: Complete CRUD Flow

### 1. Create
```
POST /orders
Authorization: Bearer <token>
Content-Type: application/json

{
  "userId": "user-123",
  "amount": 9999,
  "items": [
    { "productId": "prod-1", "quantity": 2 }
  ]
}

Response: 201 Created
{
  "data": {
    "id": "order-456",
    "userId": "user-123",
    "amount": 9999,
    "status": "pending",
    "createdAt": "2026-01-15T10:30:00Z",
    "updatedAt": "2026-01-15T10:30:00Z"
  }
}
```

### 2. Read
```
GET /orders/order-456
Authorization: Bearer <token>

Response: 200 OK
{
  "data": {
    "id": "order-456",
    "userId": "user-123",
    "amount": 9999,
    "status": "pending",
    "createdAt": "2026-01-15T10:30:00Z",
    "updatedAt": "2026-01-15T10:30:00Z"
  }
}
```

### 3. Update
```
PATCH /orders/order-456
Authorization: Bearer <token>
Content-Type: application/json

{
  "status": "shipped"
}

Response: 200 OK
{
  "data": {
    "id": "order-456",
    "userId": "user-123",
    "amount": 9999,
    "status": "shipped",
    "createdAt": "2026-01-15T10:30:00Z",
    "updatedAt": "2026-01-15T10:35:00Z"
  }
}
```

### 4. Delete
```
DELETE /orders/order-456
Authorization: Bearer <token>

Response: 204 No Content
(empty body)
```

---

See also:
- [backend-conventions.md](backend-conventions.md) — Error handling, logging
- [CLAUDE.md](../../CLAUDE.md) — Naming conventions
