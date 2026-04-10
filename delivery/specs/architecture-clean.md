# Backend Architecture: Clean Architecture Pattern

**TL;DR**: We structure backend code into 4 layers. Each layer has a single responsibility. Layers communicate through interfaces, not concrete types.

---

## Why Clean Architecture?

**Problem we're solving:**
- Backend code gets messy: HTTP handlers mixed with business logic, database calls everywhere
- Hard to test: Can't test business logic without spinning up HTTP server or database
- Hard to change: Modifying one thing breaks many other things

**Solution: Separate concerns into layers**
- Business logic lives separately from HTTP/DB details
- Each layer has one reason to change
- Easy to test: Mock dependencies, test logic in isolation
- Easy to extend: Add new handler? New DB? Existing logic unchanged

---

## The 4 Layers

```
┌─────────────────────────────────────────┐
│  External Layer (external/)             │  HTTP Server, Database, API Clients
│  ↑         ↓                            │
├─────────────────────────────────────────┤
│  Interface Layer (internal/interface/)  │  HTTP Handlers, Database Repos
│  ↑         ↓                            │
├─────────────────────────────────────────┤
│  Usecase Layer (internal/usecase/)      │  Business Workflows, Orchestration
│  ↑         ↓                            │
├─────────────────────────────────────────┤
│  Domain Layer (internal/domain/)        │  Business Logic, Entities
└─────────────────────────────────────────┘
```

### Layer 1: Domain (internal/domain/)

**What**: Pure business logic. No HTTP. No database. No external services.

**Includes**:
- Entities: `type User struct { ID uuid.UUID; Email string; ... }`
- Value Objects: `type Money struct { Amount int; Currency string }`
- Business Rules: `func (u *User) IsValid() error { ... }`
- Domain Errors: Custom error types for business failures

**Does NOT include**:
- HTTP handlers
- Database queries
- API clients
- Dependency injection

**Example**:
```go
// internal/domain/user/user.go
package user

type User struct {
	ID    uuid.UUID
	Email string
	Name  string
}

// IsValid checks business rules
func (u *User) IsValid() error {
	if u.Email == "" {
		return ErrInvalidEmail
	}
	if len(u.Name) < 2 {
		return ErrInvalidName
	}
	return nil
}
```

**Why**: Business logic must be testable without infrastructure. No mocks needed.

---

### Layer 2: Usecase (internal/usecase/)

**What**: Orchestrates domain + external. Contains workflows.

**Includes**:
- Services: `type CreateUserUsecase struct { repo UserRepository; clerk ClerkClient; }`
- Business workflows: "To create a user: validate email, check duplicate, save to DB, sync to Clerk"
- Dependency injection via constructors
- Error handling (wrapping domain errors with context)

**Does NOT include**:
- HTTP-specific code (no *gin.Context)
- Database-specific code (that's in Interface layer)

**Example**:
```go
// internal/usecase/user/create.go
package user

type CreateUserUsecase struct {
	repo UserRepository
	clerk ClerkClient
}

func NewCreateUserUsecase(repo UserRepository, clerk ClerkClient) *CreateUserUsecase {
	return &CreateUserUsecase{repo, clerk}
}

func (uc *CreateUserUsecase) Execute(ctx context.Context, email, name string) (*domain.User, error) {
	// 1. Create domain entity
	user := &domain.User{
		ID:    uuid.New(),
		Email: email,
		Name:  name,
	}

	// 2. Validate business rules
	if err := user.IsValid(); err != nil {
		return nil, fmt.Errorf("invalid user: %w", err)
	}

	// 3. Check duplicate via repository
	existing, err := uc.repo.FindByEmail(ctx, email)
	if err != nil && !errors.Is(err, ErrNotFound) {
		return nil, fmt.Errorf("failed to check duplicate: %w", err)
	}
	if existing != nil {
		return nil, ErrDuplicateEmail
	}

	// 4. Sync to external service (Clerk)
	clerkID, err := uc.clerk.CreateUser(ctx, email, name)
	if err != nil {
		return nil, fmt.Errorf("failed to sync to Clerk: %w", err)
	}

	// 5. Save to database
	user.ClerkID = clerkID
	if err := uc.repo.Save(ctx, user); err != nil {
		return nil, fmt.Errorf("failed to save user: %w", err)
	}

	return user, nil
}
```

**Why**: Business workflows are testable. Mock the repository and Clerk client.

---

### Layer 3: Interface (internal/interface/)

**What**: HTTP handlers and database repositories. Converts between HTTP/DB and domain types.

**Includes**:
- HTTP handlers: `func (h *Handler) CreateUser(c *gin.Context)`
- Database repositories: `type PostgresUserRepository struct { db *sql.DB }`
- Request/response types
- Input validation (convert HTTP to domain)

**Does NOT include**:
- Business logic (that's in Usecase)
- Business rules (that's in Domain)

**Example**:
```go
// internal/interface/handler/user.go
package handler

type Handler struct {
	createUserUsecase *usecase.CreateUserUsecase
}

func NewHandler(createUserUsecase *usecase.CreateUserUsecase) *Handler {
	return &Handler{createUserUsecase}
}

func (h *Handler) CreateUser(c *gin.Context) {
	// 1. Parse request
	var req struct {
		Email string `json:"email" binding:"required"`
		Name  string `json:"name" binding:"required"`
	}
	if err := c.BindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, ErrorResponse{
			Code:    "INVALID_INPUT",
			Message: "email and name required",
		})
		return
	}

	// 2. Call usecase (business logic)
	user, err := h.createUserUsecase.Execute(c.Request.Context(), req.Email, req.Name)
	if err != nil {
		// Handle domain errors, convert to HTTP errors
		if errors.Is(err, domain.ErrDuplicateEmail) {
			c.JSON(http.StatusConflict, ErrorResponse{
				Code:    "DUPLICATE_EMAIL",
				Message: "email already exists",
			})
			return
		}
		c.JSON(http.StatusInternalServerError, ErrorResponse{
			Code:    "INTERNAL_ERROR",
			Message: "failed to create user",
		})
		return
	}

	// 3. Convert domain entity to response
	c.JSON(http.StatusCreated, UserResponse{
		ID:    user.ID,
		Email: user.Email,
		Name:  user.Name,
	})
}

// internal/interface/repository/user.go
type PostgresUserRepository struct {
	db *sql.DB
}

func (r *PostgresUserRepository) Save(ctx context.Context, user *domain.User) error {
	// Raw SQL or ORM (Bun) call
	// Converts domain.User to DB row
	_, err := r.db.ExecContext(ctx, 
		"INSERT INTO users (id, email, name) VALUES ($1, $2, $3)",
		user.ID, user.Email, user.Name,
	)
	return err
}

func (r *PostgresUserRepository) FindByEmail(ctx context.Context, email string) (*domain.User, error) {
	// Query DB, convert row to domain.User
	var user domain.User
	err := r.db.QueryRowContext(ctx,
		"SELECT id, email, name FROM users WHERE email = $1",
		email,
	).Scan(&user.ID, &user.Email, &user.Name)
	if err == sql.ErrNoRows {
		return nil, ErrNotFound
	}
	return &user, err
}
```

**Why**: HTTP and DB details don't leak into business logic.

---

### Layer 4: External (external/)

**What**: Third-party services, databases, frameworks.

**Includes**:
- Database drivers: PostgreSQL client, migration runner
- API clients: Clerk SDK, Stripe SDK
- Framework setup: Gin router, middleware

**Does NOT include**:
- Business logic
- Even repository implementations (those are in Interface layer, external layer just provides the client)

**Example**:
```go
// external/database/postgres.go
package database

import "github.com/uptrace/bun"

func NewPostgresDB(dsn string) *bun.DB {
	sqldb := sql.OpenDB(pgdriver.NewConnector(pgdriver.WithDSN(dsn)))
	return bun.NewDB(sqldb)
}

// external/clerk/client.go
package clerk

import "github.com/clerk/clerk-sdk-go"

func NewClerkClient(apiKey string) *clerk.Client {
	return clerk.NewClient(apiKey)
}
```

**Why**: Easy to swap database or API service. Just replace this layer.

---

## How Layers Call Each Other

### Rule 1: Always Use Interfaces

**❌ Bad** (concrete types):
```go
type CreateUserUsecase struct {
	repo *PostgresUserRepository  // ← Concrete type, hard to test
}
```

**✅ Good** (interfaces):
```go
type UserRepository interface {
	Save(ctx context.Context, user *domain.User) error
	FindByEmail(ctx context.Context, email string) (*domain.User, error)
}

type CreateUserUsecase struct {
	repo UserRepository  // ← Interface, easy to mock
}
```

### Rule 2: Dependency Injection

**❌ Bad** (global state):
```go
var db *sql.DB // Global, hard to test

func CreateUser(email, name string) error {
	// Uses global db
}
```

**✅ Good** (inject dependencies):
```go
type CreateUserUsecase struct {
	repo UserRepository
	clerk ClerkClient
}

func NewCreateUserUsecase(repo UserRepository, clerk ClerkClient) *CreateUserUsecase {
	return &CreateUserUsecase{repo, clerk}
}

func (uc *CreateUserUsecase) Execute(ctx context.Context, email, name string) (*domain.User, error) {
	// Uses injected dependencies
}
```

### Rule 3: Error Handling with Context

Errors should flow up with context:

```go
// Domain layer: specific error
return ErrDuplicateEmail

// Usecase layer: wrap with context
if err != nil {
	return nil, fmt.Errorf("failed to save user: %w", err)
}

// Handler layer: convert to HTTP error
if errors.Is(err, domain.ErrDuplicateEmail) {
	c.JSON(http.StatusConflict, ...)
	return
}
```

---

## Real Example: Complete User Creation Flow

**Request comes in:**
```
POST /users
{ "email": "axel@example.com", "name": "Axel" }
```

**Layer by layer:**

1. **Handler (Interface)** ← HTTP entry point
   - Parse JSON request
   - Call usecase.Execute()

2. **Usecase (Orchestration)**
   - Create domain.User entity
   - Call user.IsValid() (Domain logic)
   - Call repo.FindByEmail() (Check duplicate)
   - Call clerk.CreateUser() (External service)
   - Call repo.Save() (Persist)
   - Return user

3. **Domain (Business Logic)**
   - user.IsValid() checks: email format, name length
   - Returns domain-specific errors

4. **Repository (Interface)**
   - Implements UserRepository interface
   - Converts between domain.User and database row

5. **External (Database)**
   - PostgreSQL driver executes SQL

**Response:**
```
201 Created
{
  "id": "uuid",
  "email": "axel@example.com",
  "name": "Axel"
}
```

---

## Testing Strategy

**Each layer is independently testable:**

### Test Domain
```go
func TestUserIsValid_MissingEmail(t *testing.T) {
	user := &domain.User{Email: "", Name: "Axel"}
	err := user.IsValid()
	assert.ErrorIs(t, err, domain.ErrInvalidEmail)
}
```

### Test Usecase (Mock dependencies)
```go
func TestCreateUserUsecase_Happy(t *testing.T) {
	mockRepo := &MockUserRepository{}
	mockClerk := &MockClerkClient{}
	
	uc := usecase.NewCreateUserUsecase(mockRepo, mockClerk)
	user, err := uc.Execute(ctx, "axel@example.com", "Axel")
	
	assert.NoError(t, err)
	assert.Equal(t, "axel@example.com", user.Email)
	assert.True(t, mockRepo.SaveCalled)
	assert.True(t, mockClerk.CreateUserCalled)
}
```

### Test Handler (Mock usecase)
```go
func TestCreateUserHandler_Happy(t *testing.T) {
	mockUsecase := &MockCreateUserUsecase{}
	handler := handler.NewHandler(mockUsecase)
	
	// Make HTTP request
	req, _ := http.NewRequest("POST", "/users", body)
	w := httptest.NewRecorder()
	handler.CreateUser(w, req)
	
	assert.Equal(t, http.StatusCreated, w.Code)
}
```

---

## Project Structure

```
backend/
├── cmd/api/main.go                    # Entry point
├── internal/
│   ├── domain/                        # Layer 1: Business logic
│   │   ├── user/
│   │   │   ├── user.go                # Entity + business rules
│   │   │   └── errors.go              # Domain-specific errors
│   │   └── order/
│   ├── usecase/                       # Layer 2: Orchestration
│   │   ├── user/
│   │   │   ├── create.go              # CreateUserUsecase
│   │   │   └── update.go
│   │   └── order/
│   └── interface/                     # Layer 3: HTTP + DB
│       ├── handler/
│       │   ├── user.go                # HTTP handlers
│       │   └── order.go
│       └── repository/
│           ├── user.go                # Database repositories
│           └── order.go
├── external/                          # Layer 4: External services
│   ├── database/
│   │   └── postgres.go                # DB client
│   ├── clerk/
│   │   └── client.go                  # Clerk SDK
│   └── stripe/
│       └── client.go                  # Stripe SDK
├── migrations/                        # Database migrations
├── venom/                             # Unit tests
│   ├── user_test.go
│   └── order_test.go
└── go.mod
```

---

## Common Mistakes

### ❌ Mistake 1: Business Logic in Handlers
```go
// WRONG
func (h *Handler) CreateUser(c *gin.Context) {
	// Parsing
	var req CreateUserRequest
	c.BindJSON(&req)
	
	// BUSINESS LOGIC MIXED WITH HTTP
	if err := h.db.QueryRow("SELECT...").Scan(&id); err != nil {
		// ...
	}
	// Now lots of code here
}
```

**Fix**: Move logic to Usecase
```go
// RIGHT
func (h *Handler) CreateUser(c *gin.Context) {
	var req CreateUserRequest
	c.BindJSON(&req)
	
	user, err := h.usecase.Execute(c.Request.Context(), req.Email)
	// Done, response
}
```

### ❌ Mistake 2: Passing *gin.Context to Usecase
```go
// WRONG
func (uc *CreateUserUsecase) Execute(c *gin.Context, ...) {
	// Usecase depends on HTTP framework
	// Can't test without Gin
}
```

**Fix**: Pass only what usecase needs
```go
// RIGHT
func (uc *CreateUserUsecase) Execute(ctx context.Context, email, name string) {
	// Only HTTP-agnostic context
	// Easy to test
}
```

### ❌ Mistake 3: Hard-coded Dependencies
```go
// WRONG
func CreateUser(email, name string) {
	db := sql.Open(...)  // Global, hard to test
	clerk := NewClerk(...) // Global, hard to test
}
```

**Fix**: Inject dependencies
```go
// RIGHT
type CreateUserUsecase struct {
	repo UserRepository
	clerk ClerkClient
}

func (uc *CreateUserUsecase) Execute(ctx context.Context, ...) {
	// Dependencies injected via constructor
}
```

---

## Next Steps

- Read [service-communication.md](service-communication.md) — How services call each other
- Read [backend-conventions.md](backend-conventions.md) — Naming, structure, errors
- See `.claude/agents/kiat-backend-coder.md` — Rules baked into agent system prompt
