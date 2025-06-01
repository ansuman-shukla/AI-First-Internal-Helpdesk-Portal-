# Backend Technical Documentation (Aligned with PRD)

**Overall Backend Philosophy:**

* Python-centric, leveraging FastAPI for API development and MongoDB for flexible document storage.
* Keep structure minimal, including only features aligned with PRD.
* Focus on core ticket management, AI routing, chat, and debugging/logging.

---

## I. Frameworks and Service Structure

1. **Core Application & API Layer (FastAPI)**

   * Single FastAPI application for all endpoints (no separate AI microservice). AI calls integrated via utility modules.
   * Use Pydantic models for request/response validation.

2. **Real-time Communication (WebSockets)**

   * FastAPI’s built-in WebSocket support for ticket chat and internal notifications.

3. **AI Utility Modules**

   * Separate Python modules under `services/ai/` for:

     * **HSA (Harmful/Spam Analysis)**
     * **Auto Routing Engine**
     * **Response Suggestion (RAG calls)**
     * **Misuse Pattern Detector**
   * These modules wrap any third-party LLM client (e.g., OpenAI or Google Gemini) and vector DB calls (e.g., Pinecone), but are not separate FastAPI services.

---

## II. Databases

1. **Primary Database (MongoDB)**

   * Collections: `users`, `tickets`, `messages`, `misuse_reports`, `knowledge_base`
   * Use the `motor` library for async MongoDB operations.
   * No Redis cache or Celery queues for V1—keep it simple.

2. **Vector Database (Pinecone)**

   * Only used by AI modules for RAG operations (response suggestion and self-serve bot).
   * Metadata stored alongside document vectors in MongoDB’s `knowledge_base`.

---

## III. Authentication & Authorization

1. **Authentication:**

   * **JWT (OAuth2 password flow)** via FastAPI utilities.
   * Endpoints: `/auth/login`, `/auth/logout`, `/auth/me` (no separate signup flow—users seeded or created by Admin).
   * JWT payload: `{ sub: user_id, role: user_role, exp, iat }`

2. **Authorization:**

   * **Role-Based Access Control (RBAC)** enforced via FastAPI dependencies.
   * Roles: `user`, `it_agent`, `hr_agent`, `admin`.
   * No escalation, no department reassignment beyond PRD rules.

---

## IV. Database Schema (MongoDB)

### 1. `users` Collection

```
users: {
  _id: ObjectId,
  username: String (Unique),
  email: String (Unique),
  password_hash: String,
  role: String ("user" | "it_agent" | "hr_agent" | "admin"),
  created_at: DateTime,
  updated_at: DateTime,
  is_active: Boolean,
  rate_limit_reset: DateTime (for 24h ticket limit),
  last_login: DateTime
}
```

### 2. `tickets` Collection

```
tickets: {
  _id: ObjectId,
  ticket_id: String ("TKT-<timestamp>-<random>"),
  title: String,
  description: String,
  urgency: String ("low" | "medium" | "high"),
  status: String ("open" | "assigned" | "resolved" | "closed"),
  department: String ("IT" | "HR"),
  assignee_id: ObjectId or null,
  user_id: ObjectId,
  created_at: DateTime,
  updated_at: DateTime,
  closed_at: DateTime or null,
  misuse_flag: Boolean,
  feedback: String or null
}
```

### 3. `messages` Collection

```
messages: {
  _id: ObjectId,
  ticket_id: ObjectId,
  sender_id: ObjectId,
  sender_role: String ("user" | "it_agent" | "hr_agent" | "admin"),
  message_type: String ("user_message" | "agent_message" | "system_message"),
  content: String,
  isAI: Boolean,
  feedback: String ("up" | "down" | "none"),
  timestamp: DateTime
}
```

### 4. `misuse_reports` Collection

```
misuse_reports: {
  _id: ObjectId,
  user_id: ObjectId,
  detection_date: DateTime,
  misuse_type: String ("duplicate_tickets" | "spam_content" | "abusive_language" | "jailbreak_attempt"),
  severity_level: String ("low" | "medium" | "high"),
  evidence_data: {
    ticket_ids: Array[ObjectId],
    content_samples: Array[String],
    pattern_analysis: String
  },
  admin_reviewed: Boolean,
  action_taken: String or null,
  ai_analysis_metadata: {
    model_reasoning: String,
    analysis_timestamp: DateTime
  }
}
```

### 5. `knowledge_base` Collection

```
knowledge_base: {
  _id: ObjectId,
  document_id: String (Unique),
  title: String,
  content: String,
  category: String ("IT" | "HR" | "General"),
  tags: Array[String],
  created_at: DateTime,
  updated_at: DateTime
  usage_count: Integer,
  effectiveness_score: Float
}
```

---

## V. API Endpoint Overview

> **Note:** Pydantic models (not shown here) enforce field constraints.

### Authentication Endpoints

```
POST /auth/login
- Request: { "username": string, "password": string }
- Response: { "access_token": string, "token_type": "bearer", "user": { ... } }
```

```
POST /auth/logout
- Headers: Authorization: Bearer <token>
- Response: { "message": "Logout successful" }
```

```
GET /auth/me
- Headers: Authorization: Bearer <token>
- Response: { user object without password_hash }
```

### Ticket Endpoints

```
POST /tickets
- Headers: Authorization: Bearer <token>
- Request: { title, description, urgency? }
- Response: Ticket object
- Flow:
  1. Rate limit check (count last-24h tickets)
  2. HSA module → If flagged, set misuse_flag and notify Admin, return ticket with status="open"
  3. Auto Routing → assign department & assignee_id, set status="assigned"
  4. Save to DB, return ticket
  5. Fire on_ticket_created webhook
```

```
GET /tickets
- Headers: Authorization: Bearer <token>
- Query: status?, department?, page?, limit?
- Response: { tickets: [...], total_count, pagination }
```

```
GET /tickets/{ticket_id}
- Headers: Authorization: Bearer <token>
- Response: Ticket object + messages array
```

```
PUT /tickets/{ticket_id}
- Headers: Authorization: Bearer <token>
- Request: { title?, description?, status?, department? }
- Response: Updated Ticket object
- Logic:
  - Title/Description edits only if status="open" and user is owner
  - Department change only if status="open" and user or agent
  - Status transitions: open → assigned → resolved → closed
```

```
POST /tickets/{ticket_id}/messages
- Headers: Authorization: Bearer <token>
- Request: { content, message_type, isAI }
- Response: Message object
- Logic:
  - Save message, broadcast via WebSocket, fire on_message_sent webhook
```

```
POST /tickets/{ticket_id}/resolve
- Headers: Authorization: Bearer <token>
- Response: { "message": "Ticket marked as resolved" }
- Logic: Only user can call, sets status="resolved", fire webhook
```

```
POST /tickets/{ticket_id}/close
- Headers: Authorization: Bearer <token>
- Response: { "message": "Ticket closed" }
- Logic: Only agent can call when status="resolved", sets status="closed" & closed_at, fire webhook
```

### AI Endpoints (Internal use)

```
POST /ai/suggest-response
- Headers: Authorization: Bearer <token>
- Request: { ticket_id, conversation_context }
- Response: { suggested_response: string }
- Logic: RAG query, return draft with isAI=true, fire on_ai_reply_suggested webhook
```

```
POST /ai/self-serve-query
- Request: { query, session_id? }
- Response: { answer: string }
- Logic: RAG query, return answer with isAI=true
```

### Admin Endpoints

```
GET /admin/misuse-reports
- Headers: Authorization: Bearer <token>
- Response: Array of misuse_report objects
```

```
POST /admin/mark-reviewed
- Headers: Authorization: Bearer <token>
- Request: { report_id }
- Response: { "message": "Marked as reviewed" }
```

---

## VI. WebSocket Events

```
1. new_message_in_ticket: { ticket_id, message: Message }
2. ticket_status_changed: { ticket_id, old_status, new_status }
3. ticket_assigned: { ticket_id, agent_id }
4. new_ticket_for_agent: { ticket: Ticket }
5. misuse_detected: { user_id, report }
```

* Authentication: JWT token passed during WebSocket handshake.
* Channel mapping: One room per ticket (`ticket_<ticket_id>`), one admin room (`admin_alerts`), one agent queue room per department (`agents_IT`, `agents_HR`).

---

## VII. Error Handling & Debugging

### 1. Error Response Format

```
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable description",
    "details": "Technical details (optional)",
    "timestamp": "ISO 8601",
    "request_id": "UUID",
    "context": {
      "user_id": "<user_id>",
      "endpoint": "<path>",
      "method": "<HTTP method>"
    }
  }
}
```

**Key Error Codes:**

* `AUTH_INVALID`
* `AUTHZ_FORBIDDEN`
* `VALIDATION_ERROR`
* `RATE_LIMIT_EXCEEDED`
* `AI_PROCESSING_ERROR`
* `DB_ERROR`
* `WS_ERROR`

### 2. Logging Strategy

* **Structured JSON logs** with fields:

  * `timestamp` (ISO 8601)
  * `level` (`DEBUG`, `INFO`, `WARN`, `ERROR`)
  * `module` (`auth`, `ticket_service`, `ai_service`, `ws_service`)
  * `request_id` (UUID)
  * `user_id` (if available)
  * `event` (short description)
  * `data` (contextual info)
  * `duration_ms` (optional)

* **Log Retention:** handled by infrastructure; focus on capturing sufficient context for debugging.

---

**Updates from Original Draft:**

1. **Removed**: Redis cache and Celery — not needed for V1.
2. **Merged AI services** into core application under `services/ai/` — no separate FastAPI for AI.
3. **Removed**: Detailed attachment schema — file uploads are out of scope per PRD.
4. **Simplified**: Department/escalation flows — only changes permitted while status="open".
5. **Eliminated**: SLA, attachments, audit\_logs, verbose analytics — out of scope.
6. **Retained**: Error handling & logging frameworks (core for debugging).

---
