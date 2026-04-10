# Architecture Overview: Start Here

This directory contains architectural guidelines for the backend and frontend.

---

## 📚 Read These (In Order)

### Backend

1. **[architecture-clean.md](architecture-clean.md)** — How we structure the Go backend
   - Why Clean Architecture?
   - The 4 layers (Domain, Usecase, Interface, External)
   - How layers communicate
   - Real examples from the codebase

2. **[service-communication.md](service-communication.md)** — How services call each other
   - Dependency injection pattern
   - Error handling across layers
   - Interface-based design

3. **[backend-conventions.md](backend-conventions.md)** — Standards and naming
   - Project structure (where files live)
   - Function/type naming
   - Error codes
   - Logging format

### Frontend

- **frontend/ARCHITECTURE.md** (in your frontend directory)
  - Server vs Client components
  - Folder structure
  - Hook patterns

---

## 🔗 For Agents

Agents read the **concise, baked-in versions**:
- Backend-Coder: Extracts from these docs into system prompt
- Frontend-Coder: Similar for frontend
- Reviewers: Reference these to verify compliance

See: [../.claude/agents/README.md](../../.claude/agents/README.md)

---

## 🎯 Key Principle

- **This directory** = detailed reference (for humans)
- **Agent system prompts** = extracted critical rules (for agents)
- Both reference each other

---

**Start with [architecture-clean.md](architecture-clean.md).**
