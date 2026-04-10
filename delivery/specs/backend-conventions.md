# Backend Conventions: Go + Gin + Bun ORM

Naming, structure, error handling, and logging standards for consistent, maintainable backend code.

---

## Project Structure

```
backend/
├── cmd/api/
│   └── main.go                    # Entry point: setup layers, wire services, start server
├── internal/
│   ├── domain/                    # Layer 1: Business logic, entities, errors
│   │   ├── user/
│   │   │   ├── user.go            # User entity, IsValid(), business rules
│   │   │   ├── errors.go          # ErrInvalidEmail, ErrDuplicateEmail, etc.
│   │   │   └── repository.go      # UserRepository interface
│   │   └── order/
│   ├── usecase/                   # Layer 2: Orchestration, services
│   │   ├── user/
│   │   │   ├── create.go          # CreateUserUsecase
│   │   │   └── get.go             # GetUserUsecase
│   │   └── order/
│   └── interface/                 # Layer 3: HTTP + Database
│       ├── handler/
│       │   ├── user.go            # HTTP handlers (REST endpoints)
│       │   └── error.go           # ErrorResponse, error conversion helpers
│       └── repository/
│           ├── user.go            # PostgresUserRepository implementation
│           └── order.go
├── external/                      # Layer 4: External services
│   ├── database/
│   │   └── postgres.go            # Database client setup
│   ├── clerk/
│   │   └── client.go              # Clerk SDK wrapper
│   └── middleware/
│       ├── logging.go             # Request logging
│       ├── auth.go                # Clerk JWT verification
│       └── rate_limit.go          # Rate limiting
├── migrations/
│   ├── 001_create_users.sql
│   └── 002_create_orders.sql
├── venom/                         # Unit tests
│   ├── user_test.go
│   └── order_test.go
├── go.mod
└── go.sum
```

**Key rules:**
- Domain layer: `internal/domain/{entity}/` — one package per domain entity
- Usecase layer: `internal/usecase/{entity}/` — orchestration logic
- Interface layer: `internal/interface/{handler,repository}/` — HTTP + DB
- External layer: `external/` — clients, middleware, setup
- Tests: `venom/` — use table-driven tests, seed helpers, database fixtures

---

## Naming Conventions

### Packages and Files

**Domain packages**: Entity name (lowercase, singular)
```go
package user        // internal/domain/user/
package order       // internal/domain/order/
```

**Handler files**: Entity name, contains HTTP handlers
```go
// internal/interface/handler/user.go
type UserHandler struct { ... }
func (h *UserHandler) CreateUser(c *gin.Context) { ... }
func (h *UserHandler) GetUser(c *gin.Context) { ... }
```

**Repository files**: Entity name, contains interface + implementation
```go
// internal/interface/repository/user.go
type UserRepository interface { ... }
type PostgresUserRepository struct { ... }
```

**Service files**: Usecase name, describes action
```go
// internal/usecase/user/create.go
type CreateUserUsecase struct { ... }
func (uc *CreateUserUsecase) Execute(ctx context.Context, ...) { ... }

// internal/usecase/user/get.go
type GetUserUsecase struct { ... }
```

### Types and Interfaces

**Structs**: PascalCase, descriptive
```go
type User struct { }
type CreateUserRequest struct { }
type UserResponse struct { }
type PostgresUserRepository struct { }
type CreateUserUsecase struct { }
```

**Interfaces**: PascalCase, action-oriented (Verb + Noun) or role-based (Noun + "er")
```go
type UserRepository interface { }       // Role-based
type PaymentProcessor interface { }     // Role-based
type UserValidator interface { }        // Role-based
```

**Receivers**: Single letter (u, h, r, uc, s)
```go
func (u *User) IsValid() error { }                          // u = user entity
func (h *UserHandler) CreateUser(c *gin.Context) { }       // h = handler
func (r *PostgresUserRepository) Save(ctx...) error { }    // r = repository
func (uc *CreateUserUsecase) Execute(ctx...) (*User, error) { }  // uc = usecase
```

**Function names**: Descriptive, action-oriented
```go
// Good
func (uc *CreateUserUsecase) Execute(ctx context.Context, email, name string) (*User, error)
func (r *PostgresUserRepository) FindByEmail(ctx context.Context, email string) (*User, error)
func (h *UserHandler) CreateUser(c *gin.Context)

// Bad (vague)
func (uc *CreateUserUsecase) Do(ctx context.Context, ...) (*User, error)
func (r *PostgresUserRepository) Get(ctx context.Context, email string) (*User, error)
func (h *UserHandler) Handle(c *gin.Context)
```

### Variables

**Context**: Always `ctx`
```go
func (uc *CreateUserUsecase) Execute(ctx context.Context, ...) { }
```

**Errors**: `err`
```go
if err := repo.Save(ctx, user); err != nil {
    return nil, fmt.Errorf("failed to save user: %w", err)
}
```

**Request/Response**: `req`, `res`, `resp`
```go
var req CreateUserRequest
if err := c.BindJSON(&req); err != nil { }

c.JSON(http.StatusCreated, UserResponse{ ... })
```

**Interface values**: Descriptive name
```go
type UserService interface { }
var service UserService = &CreateUserUsecase{ }  // OK
var userService UserService = &CreateUserUsecase{ }  // Better
```

---

## Error Codes and HTTP Status Mapping

**Use these error codes consistently across your API.** Errors flow from domain → usecase → handler, converting to HTTP status.

### Domain Layer Errors

Define in `internal/domain/{entity}/errors.go`:

```go
package user

var (
    ErrInvalidEmail    = errors.New("email is invalid")
    ErrInvalidName     = errors.New("name is too short")
    ErrDuplicateEmail  = errors.New("email already exists")
    ErrNotFound        = errors.New("user not found")
)
```

### HTTP Error Codes and Statuses

| Error Code | HTTP Status | Meaning | Example |
|---|---|---|---|
| INVALID_INPUT | 400 Bad Request | Input validation failed (missing field, format error) | Missing email in request body |
| INVALID_EMAIL | 400 Bad Request | Specific: invalid email format | "notanemail" |
| INVALID_NAME | 400 Bad Request | Specific: invalid name (too short, contains numbers, etc.) | Name length < 2 |
| DUPLICATE_EMAIL | 409 Conflict | Email already exists | POST /users with existing email |
| NOT_FOUND | 404 Not Found | Resource doesn't exist | GET /users/:id with invalid ID |
| UNAUTHORIZED | 401 Unauthorized | Missing or invalid authentication (JWT expired, missing token) | No Authorization header |
| FORBIDDEN | 403 Forbidden | Authenticated but not allowed (RLS denied, insufficient permissions) | User A reading User B's data |
| RATE_LIMITED | 429 Too Many Requests | Rate limit exceeded | Too many requests in time window |
| INTERNAL_ERROR | 500 Internal Server Error | Server error, don't leak details | Database connection failure |
| SERVICE_UNAVAILABLE | 503 Service Unavailable | External service down (Clerk, Stripe, S3) | Clerk API timeout |

### Handler Error Conversion Example

```go
func (h *UserHandler) CreateUser(c *gin.Context) {
    var req CreateUserRequest
    if err := c.BindJSON(&req); err != nil {
        c.JSON(http.StatusBadRequest, ErrorResponse{
            Code:    "INVALID_INPUT",
            Message: "missing required fields",
        })
        return
    }

    user, err := h.usecase.Execute(c.Request.Context(), req.Email, req.Name)
    if err != nil {
        // Check specific domain errors
        if errors.Is(err, domain.ErrDuplicateEmail) {
            c.JSON(http.StatusConflict, ErrorResponse{
                Code:    "DUPLICATE_EMAIL",
                Message: "email already in use",
            })
            return
        }
        if errors.Is(err, domain.ErrInvalidEmail) {
            c.JSON(http.StatusBadRequest, ErrorResponse{
                Code:    "INVALID_EMAIL",
                Message: "email format is invalid",
            })
            return
        }

        // Generic server error (don't leak details)
        log.WithError(err).Error("failed to create user")
        c.JSON(http.StatusInternalServerError, ErrorResponse{
            Code:    "INTERNAL_ERROR",
            Message: "failed to create user",
        })
        return
    }

    c.JSON(http.StatusCreated, UserResponse{
        ID:    user.ID,
        Email: user.Email,
        Name:  user.Name,
    })
}
```

---

## Logging Format and Fields

Use structured logging with consistent field names. Examples: `logrus`, `zap`, or Go's `slog`.

### Log Levels

- **ERROR**: Business logic failed (duplicate email, user not found, external service down)
- **WARN**: Degraded behavior (slow query, retry attempt, partial failure)
- **INFO**: Audit events (user created, data modified, auth success)
- **DEBUG**: Development only (SQL queries, DI setup, cache hits)

### Required Fields

Every log entry should include:

```go
log.WithFields(map[string]interface{}{
    "trace_id":     traceID,          // From request context, for debugging
    "user_id":      userID,           // If authenticated (masked in error responses)
    "action":       "create_user",    // What happened
    "status":       "success",        // success, error, retry
    "duration_ms":  responseTime,     // How long it took
    "error_code":   "DUPLICATE_EMAIL", // Error code if failed (not HTTP status)
}).Info("user created")
```

### Examples

**Success**:
```go
log.WithFields(map[string]interface{}{
    "action":      "create_user",
    "user_id":     user.ID,
    "duration_ms": time.Since(start).Milliseconds(),
}).Info("user created successfully")
```

**Domain error** (expected, not alarming):
```go
log.WithFields(map[string]interface{}{
    "action":      "create_user",
    "error_code":  "DUPLICATE_EMAIL",
    "email":       email, // OK to log (not a secret)
    "duration_ms": time.Since(start).Milliseconds(),
}).Warn("user creation failed: duplicate email")
```

**Server error** (unexpected, alarming):
```go
log.WithFields(map[string]interface{}{
    "action":      "create_user",
    "error_code":  "INTERNAL_ERROR",
    "error":       err.Error(), // Full error details in logs (private)
    "trace_id":    traceID,     // For debugging
    "duration_ms": time.Since(start).Milliseconds(),
}).Error("failed to create user")
```

### What NOT to Log

- **Secrets**: Passwords, API keys, tokens, PII (emails, phone numbers)
  ```go
  // BAD
  log.WithFields(map[string]interface{}{
      "password": password, // ❌ NEVER log passwords
      "token":    clerkToken, // ❌ NEVER log tokens
  }).Info("user signing in")

  // GOOD
  log.WithFields(map[string]interface{}{
      "user_id":   userID, // ✅ OK (masked identifier)
      "action":    "sign_in", // ✅ OK (action, no details)
  }).Info("user signed in")
  ```

---

## Database Conventions

### Migrations

Place migrations in `backend/migrations/` with sequential numbering:

```
migrations/
├── 001_create_users.sql
├── 002_create_orders.sql
└── 003_add_indexes.sql
```

**Naming**: `NNN_description.sql` (3-digit number, snake_case description)

**Content**:
```sql
-- 001_create_users.sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);

-- Run with: go run cmd/api/main.go --migrate
```

### Row-Level Security (RLS)

Enable RLS on all tables to prevent data leakage:

```sql
-- Enable RLS
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only see their own data
CREATE POLICY user_own_data ON users
    FOR SELECT USING (id = current_user_id());

-- Policy: Service role (superuser) bypasses RLS
GRANT ALL ON users TO service_role;
```

**Service role**: Migrations and backend API run as `service_role` (superuser) which bypasses RLS. RLS is enforced at HTTP API layer via Clerk JWT + `current_user_id()` function.

### Timestamps

Use `time.RFC3339Nano` for microsecond precision:

```go
// Domain
type User struct {
    ID        uuid.UUID
    Email     string
    CreatedAt time.Time  // time.RFC3339Nano
    UpdatedAt time.Time  // time.RFC3339Nano
}

// Repository INSERT
_, err := db.NewInsert().Model(user).Exec(ctx)

// Repository UPDATE with optimistic locking
_, err := db.NewUpdate().
    Model(user).
    Where("id = ? AND updated_at = ?", user.ID, user.UpdatedAt).
    Exec(ctx)
if err != nil {
    return fmt.Errorf("conflict: optimistic lock failed: %w", err)
}

// Bun Note: Comparing timestamps for optimistic locking?
// Use Truncate(time.Microsecond) to ignore nanoseconds
if !user.UpdatedAt.Truncate(time.Microsecond).Equal(dbUpdatedAt.Truncate(time.Microsecond)) {
    return ErrConflict
}
```

---

## Handler Patterns

### Route Registration

In `main.go`, register routes **after** dependency injection setup:

```go
func main() {
    // Setup layers
    db := setupDatabase()
    clerkClient := clerk.NewClient(os.Getenv("CLERK_API_KEY"))
    
    userRepo := &repository.PostgresUserRepository{DB: db}
    createUserUsecase := &usecase.CreateUserUsecase{Repo: userRepo, Clerk: clerkClient}
    userHandler := &handler.UserHandler{CreateUserUsecase: createUserUsecase}
    
    // Setup router
    r := gin.New()
    r.Use(middleware.LoggingMiddleware())
    r.Use(middleware.AuthMiddleware())
    
    // Register routes
    r.POST("/users", userHandler.CreateUser)
    r.GET("/users/:id", userHandler.GetUser)
    r.PATCH("/users/:id", userHandler.UpdateUser)
    r.DELETE("/users/:id", userHandler.DeleteUser)
    
    r.Run(":8080")
}
```

**CRITICAL**: Verify every handler is registered. Agents may forget to wire handlers in main.go—review CI logs carefully.

### Handler Method Signature

```go
func (h *UserHandler) CreateUser(c *gin.Context) {
    // 1. Parse request
    var req CreateUserRequest
    if err := c.BindJSON(&req); err != nil {
        c.JSON(http.StatusBadRequest, ErrorResponse{Code: "INVALID_INPUT", Message: "..."})
        return
    }

    // 2. Call usecase
    user, err := h.createUserUsecase.Execute(c.Request.Context(), req.Email, req.Name)
    if err != nil {
        // Handle errors
    }

    // 3. Return response
    c.JSON(http.StatusCreated, UserResponse{...})
}
```

---

## Testing Patterns (Venom)

Place unit tests in `venom/` directory using table-driven tests:

```go
// venom/user_test.go
func TestCreateUserUsecase(t *testing.T) {
    tests := []struct {
        name    string
        email   string
        wantErr bool
    }{
        {"valid email", "test@example.com", false},
        {"invalid email", "notanemail", true},
        {"empty email", "", true},
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            repo := &MockUserRepository{}
            uc := &usecase.CreateUserUsecase{Repo: repo}
            
            _, err := uc.Execute(context.Background(), tt.email, "Test")
            
            if (err != nil) != tt.wantErr {
                t.Errorf("got error %v, want error %v", err, tt.wantErr)
            }
        })
    }
}
```

**Helpers**:
- `setupTestDB()` — Connect to test database
- `seedUser()` — Create test user
- `cleanupTestData()` — Clear test tables
- Mock implementations for repositories and external clients

---

## Dependency Injection Checklist

When creating a new service, verify:

- [ ] Constructor receives all dependencies via parameters
- [ ] Constructor returns `*ServiceType`, not error
- [ ] Dependencies are interfaces, not concrete types
- [ ] Service is tested with mocks (repository, external client)
- [ ] Service error handling wraps with context
- [ ] Handler converts domain errors to HTTP status codes
- [ ] Route is registered in `main.go`

---

## Common Mistakes

### ❌ Mistake 1: Forgetting to Register Route

```go
// WRONG
func main() {
    userHandler := &handler.UserHandler{...}
    // Forgot to register the route!
    r.Run(":8080")
}
```

**Fix**: Always register routes in main.go after handler setup.

### ❌ Mistake 2: Handler Calling Repository Directly

```go
// WRONG
type UserHandler struct {
    repo UserRepository  // ← Should go through usecase
}

func (h *UserHandler) CreateUser(c *gin.Context) {
    user := &User{Email: req.Email}
    h.repo.Save(c.Request.Context(), user)  // ← No validation, no orchestration
}
```

**Fix**: Handler calls usecase, usecase calls repository.

### ❌ Mistake 3: Not Wrapping Errors with Context

```go
// WRONG
if err != nil {
    return nil, err  // ← Lost context, hard to debug
}

// GOOD
if err != nil {
    return nil, fmt.Errorf("failed to save user: %w", err)  // ← Context preserved
}
```

### ❌ Mistake 4: Leaking Domain Errors in HTTP

```go
// WRONG
if err == ErrDuplicateEmail {
    c.JSON(http.StatusConflict, err)  // ← Exposes internal error type
}

// GOOD
if errors.Is(err, domain.ErrDuplicateEmail) {
    c.JSON(http.StatusConflict, ErrorResponse{
        Code:    "DUPLICATE_EMAIL",
        Message: "email already in use",
    })
}
```

---

## Summary: Backend Conventions Should

✅ Follow folder structure (domain → usecase → interface → external)  
✅ Use consistent naming (types: PascalCase, packages: lowercase, functions: Verb+Noun)  
✅ Define domain errors in domain layer  
✅ Convert errors to HTTP in handler layer  
✅ Use structured logging with trace_id, user_id, action, status  
✅ Enable RLS on all database tables  
✅ Use `time.RFC3339Nano` for timestamps  
✅ Inject dependencies via constructors  
✅ Test with mocks (repository, external client)  
✅ Register routes in main.go (agents often forget this)

❌ Mix business logic in handlers  
❌ Pass *gin.Context to usecase  
❌ Use global state for dependencies  
❌ Leak domain errors to HTTP responses  
❌ Forget route registration  
❌ Log secrets or PII

---

See also:
- [architecture-clean.md](architecture-clean.md) — The 4 layers explained
- [service-communication.md](service-communication.md) — Dependency injection patterns
- [CLAUDE.md](../../.claude/docs/CLAUDE.md) — General naming and git conventions
