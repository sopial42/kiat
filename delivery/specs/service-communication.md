# Service Communication Patterns

How services talk to each other, what dependencies look like, error handling across layers.

---

## Dependency Injection Pattern

**Principle**: Services receive dependencies at construction time, not global state or lazy initialization.

### Constructor Injection (Recommended)

```go
// ✅ GOOD
type UserService struct {
	userRepo  UserRepository
	authRepo  AuthRepository
	clerkAPI  ClerkClient
}

func NewUserService(
	userRepo UserRepository,
	authRepo AuthRepository,
	clerkAPI ClerkClient,
) *UserService {
	return &UserService{
		userRepo:  userRepo,
		authRepo:  authRepo,
		clerkAPI:  clerkAPI,
	}
}

func (s *UserService) Create(ctx context.Context, email, name string) (*User, error) {
	// Use injected dependencies
	user := &User{Email: email, Name: name}
	if err := s.userRepo.Save(ctx, user); err != nil {
		return nil, err
	}
	if err := s.clerkAPI.SyncUser(ctx, user.ID, email); err != nil {
		return nil, err
	}
	return user, nil
}
```

### In main.go

```go
func main() {
	// Setup layers bottom-up
	
	// External layer: clients
	db := setupPostgres()
	clerkClient := clerk.NewClient(os.Getenv("CLERK_API_KEY"))
	
	// Repository (Interface layer)
	userRepo := &repository.PostgresUserRepository{DB: db}
	authRepo := &repository.PostgresAuthRepository{DB: db}
	
	// Services (Usecase layer)
	userService := &usecase.UserService{
		userRepo: userRepo,
		authRepo: authRepo,
		clerkAPI: clerkClient,
	}
	
	// Handlers (Interface layer)
	userHandler := &handler.UserHandler{
		userService: userService,
	}
	
	// HTTP server (External layer)
	r := gin.New()
	r.POST("/users", userHandler.Create)
	r.Run(":8080")
}
```

---

## Interface-Based Design

**Principle**: Depend on interfaces, not concrete types.

### ❌ Bad: Depend on Concrete Type

```go
type UserService struct {
	repo *repository.PostgresUserRepository  // ← Concrete, tightly coupled
}

func NewUserService(repo *repository.PostgresUserRepository) *UserService {
	return &UserService{repo}
}

// Problem: UserService is tied to PostgreSQL
// Hard to test: Must set up real PostgreSQL
// Hard to change: Switching to MySQL requires rewriting UserService
```

### ✅ Good: Depend on Interface

```go
type UserRepository interface {
	Save(ctx context.Context, user *User) error
	FindByID(ctx context.Context, id uuid.UUID) (*User, error)
	FindByEmail(ctx context.Context, email string) (*User, error)
}

type UserService struct {
	repo UserRepository  // ← Interface, loosely coupled
}

func NewUserService(repo UserRepository) *UserService {
	return &UserService{repo}
}

// Benefit: UserService works with any UserRepository
// Easy to test: Mock UserRepository in tests
// Easy to change: Swap PostgreSQL for MySQL, no UserService changes
```

### Testing with Mocks

```go
type MockUserRepository struct {
	SaveCalled bool
	SaveUser   *User
}

func (m *MockUserRepository) Save(ctx context.Context, user *User) error {
	m.SaveCalled = true
	m.SaveUser = user
	return nil
}

func TestUserService_Create(t *testing.T) {
	mockRepo := &MockUserRepository{}
	service := usecase.NewUserService(mockRepo)
	
	user, err := service.Create(context.Background(), "test@example.com", "Test")
	
	assert.NoError(t, err)
	assert.True(t, mockRepo.SaveCalled)
	assert.Equal(t, "test@example.com", mockRepo.SaveUser.Email)
}
```

---

## Error Handling Across Layers

**Principle**: Errors flow up. Each layer wraps with context, converts at boundaries.

### Layer 1: Domain Errors

Domain layer defines specific errors:

```go
// internal/domain/user/errors.go
package user

var (
	ErrInvalidEmail   = errors.New("email is invalid")
	ErrInvalidName    = errors.New("name is too short")
	ErrDuplicateEmail = errors.New("email already exists")
)
```

### Layer 2: Usecase Wraps with Context

Usecase catches domain errors and wraps with context:

```go
func (s *UserService) Create(ctx context.Context, email, name string) (*User, error) {
	user := &User{Email: email, Name: name}
	
	// Domain validation
	if err := user.IsValid(); err != nil {
		return nil, fmt.Errorf("user validation failed: %w", err)
		// Now: "user validation failed: email is invalid"
	}
	
	// Repository call
	existing, err := s.repo.FindByEmail(ctx, email)
	if err != nil && !errors.Is(err, sql.ErrNoRows) {
		return nil, fmt.Errorf("failed to check email: %w", err)
	}
	if existing != nil {
		return nil, fmt.Errorf("email already in use: %w", domain.ErrDuplicateEmail)
	}
	
	// External service call
	if err := s.clerkAPI.CreateUser(ctx, email, name); err != nil {
		return nil, fmt.Errorf("failed to sync with Clerk: %w", err)
	}
	
	return user, nil
}
```

### Layer 3: Handler Converts to HTTP

Handler catches business errors and converts to HTTP status:

```go
func (h *UserHandler) Create(c *gin.Context) {
	var req CreateUserRequest
	if err := c.BindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, ErrorResponse{
			Code:    "INVALID_INPUT",
			Message: "missing required fields",
		})
		return
	}
	
	user, err := h.service.Create(c.Request.Context(), req.Email, req.Name)
	
	// Check for specific business errors
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
	if err != nil {
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

## Service Composition Example

How would OrderService interact with UserService?

```go
// internal/domain/order/order.go
type Order struct {
	ID     uuid.UUID
	UserID uuid.UUID  // Reference to user
	Amount int
}

// internal/usecase/order/order.go
type OrderService struct {
	orderRepo    OrderRepository
	userRepo     UserRepository  // ← Can also depend on repository directly
	// OR
	userService  *user.UserService  // ← Or depend on another service
	
	paymentAPI   PaymentClient
}

// Two approaches:

// Approach 1: OrderService calls UserRepository directly
func (s *OrderService) Create(ctx context.Context, userID uuid.UUID, amount int) (*Order, error) {
	// Check user exists
	user, err := s.userRepo.FindByID(ctx, userID)
	if err != nil {
		return nil, fmt.Errorf("user not found: %w", err)
	}
	
	// Proceed with order logic
	order := &Order{ID: uuid.New(), UserID: user.ID, Amount: amount}
	return order, s.orderRepo.Save(ctx, order)
}

// Approach 2: OrderService calls UserService
func (s *OrderService) Create(ctx context.Context, userID uuid.UUID, amount int) (*Order, error) {
	// Verify user is valid (UserService might do additional logic)
	user, err := s.userService.GetByID(ctx, userID)
	if err != nil {
		return nil, fmt.Errorf("failed to get user: %w", err)
	}
	
	// Proceed with order logic
	order := &Order{ID: uuid.New(), UserID: user.ID, Amount: amount}
	return order, s.orderRepo.Save(ctx, order)
}
```

**Which is better?**
- **Approach 1** (direct repo): Simpler, fewer dependencies, lighter coupling
- **Approach 2** (service): Useful if UserService has complex logic OrderService needs

Use Approach 1 by default, switch to Approach 2 if there's real business logic to share.

---

## Middleware & Cross-Cutting Concerns

Some code runs on every request (logging, auth, error recovery). Where does it go?

### Setup in HTTP Server

```go
func main() {
	r := gin.New()
	
	// Middleware (External layer: HTTP setup)
	r.Use(LoggingMiddleware())        // Structured logging
	r.Use(AuthMiddleware())           // Verify Clerk JWT
	r.Use(ErrorRecoveryMiddleware())  // Panic recovery
	r.Use(RateLimitMiddleware())      // Rate limiting
	
	// Routes
	r.POST("/users", userHandler.Create)
	
	r.Run(":8080")
}

// Middleware functions (external/middleware/)
func LoggingMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		start := time.Now()
		
		c.Next()
		
		log.WithFields(map[string]interface{}{
			"method":   c.Request.Method,
			"path":     c.Request.URL.Path,
			"status":   c.Writer.Status(),
			"duration": time.Since(start),
		}).Info("request handled")
	}
}

func AuthMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		token := c.GetHeader("Authorization")
		// Verify token
		userID, err := VerifyClerkToken(token)
		if err != nil {
			c.JSON(http.StatusUnauthorized, ...)
			c.Abort()
			return
		}
		
		// Store in context for handler to access
		c.Set("user_id", userID)
		c.Next()
	}
}
```

---

## Summary: Service Dependencies Should

✅ Be received via constructor  
✅ Be interfaces, not concrete types  
✅ Be tested with mocks  
✅ Have errors wrapped with context at each layer  
✅ Be converted to HTTP at handler boundary  

❌ Be global state  
❌ Be concrete types  
❌ Be lazily initialized  
❌ Be directly accessed across layers  

---

See also: [architecture-clean.md](architecture-clean.md) for the full layer breakdown.
