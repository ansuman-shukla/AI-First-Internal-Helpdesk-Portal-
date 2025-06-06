**Product Requirements Document (PRD)**

---

**Project Title:** Internal AI-Powered Helpdesk System (MVP)

**Owner:** \[User]

**Goal:**
Build a simple, internal ticket-based helpdesk system for IT, HR, and Admin queries, enhanced with AI routing, response suggestion, a self-serve bot, and spam/misuse detection. Focus is on rapid development and core functionality over scalability or extraneous features.

**Attributes:**

* **isAI:** Boolean attribute on each message indicating if it was generated by AI.
* **Feedback:** Each message in a conversation has an `feedback` attribute with values `up` or `down` to capture user/agent feedback.

---

## 1. User Roles and Authentication

### Roles:

* **User:** Submits and manages tickets.
* **IT Agent:** Handles IT tickets.
* **HR Agent:** Handles HR tickets.
* **Admin:** Oversees system usage, receives misuse reports.

### Authentication:

* Simple login-based authentication using JWT.
* Role-based access control (no role impersonation).

---

## 2. Ticket Lifecycle

### Ticket Fields:

* `ticket_id`: String (Auto-generated, e.g., "TKT-<timestamp>-<random>").
* `title`: String (Required, max 200 chars).
* `description`: String (Required, max 2000 chars).
* `urgency`: Enum (`low`, `medium` (default), `high`).
* `status`: Enum (`open`, `assigned`, `resolved`, `closed`).
* `department`: Enum (`IT`, `HR`). Populated by LLM router; can be changed manually by user or agent only while `status = open`.
* `assignee_id`: Reference to users.\_id (agent assigned to ticket).
* `user_id`: Reference to users.\_id (ticket creator).
* `created_at`: DateTime (Auto-generated).
* `updated_at`: DateTime (Auto-updated).
* `closed_at`: DateTime (Set when status = `closed`).
* `misuse_flag`: Boolean (Default: false; set by misuse detector).
* `feedback`: String (Optional; post-resolution rating by user or agent).

### Ticket Flow:

1. **Creation**: User creates a ticket by providing `title`, `description`, and optional `urgency`. System sets `status = open` and `department` pending routing.
2. **HSA Check**: Content passes through Harmful/Spam Analysis. If flagged (`misuse_flag = true`), Admin is notified and ticket is not routed further.
3. **Routing**: LLM router assigns `department = IT` or `HR` (compulsory, no confidence score). System sets `status = assigned` and `assignee_id` = sole agent in that department.
4. **Conversation**: User and assigned agent chat in real-time within ticket. Messages include `isAI` and `feedback` attributes. Chat messages are stored for history.
5. **Resolution**: User can mark ticket `resolved`. Once marked `resolved`, only the assigned agent can change `status` to `closed`.
6. **Closure**: Agent closes ticket (`status = closed`, sets `closed_at`).

### Permissions:

* **User**: Create tickets; edit own tickets (`title`, `description`) while `status = open`; view own tickets; send messages on own tickets; rate with `feedback` after close.
* **Agents**: View and update tickets in their department; change `status` from `assigned` → `resolved` (optionally) → `closed`; send messages on assigned tickets; use AI suggestion; give message feedback.
* **Admin**: View all tickets; view misuse reports; cannot escalate or reassign; can change department only while `status = open` upon manual review.

---

## 3. Real-Time Chat (1:1)

* Chat interface within each ticket.
* Uses WebSocket for real-time messaging.
* Messages stored in `messages` collection with the following fields:

  * `message_id`: ObjectId.
  * `ticket_id`: Reference to tickets.\_id.
  * `sender_id`: Reference to users.\_id.
  * `sender_role`: Enum (`user`, `it_agent`, `hr_agent`, `admin`).
  * `message_type`: Enum (`user_message`, `agent_message`, `system_message`).
  * `content`: String (Required, max 1000 chars).
  * `isAI`: Boolean (True if generated by AI, else False).
  * `feedback`: Enum (`up`, `down`, `none`) for rating each message.
  * `timestamp`: DateTime (Auto-generated).

---

## 4. AI Modules

### 4.1. Harmful/Spam Analysis (HSA)

* Run synchronously on ticket creation.
* Checks `title` and `description` for:

  * Jailbreak prompts
  * Abusive or explicit language
  * Spam or gibberish content
* If flagged, sets `misuse_flag = true`, and triggers Admin notification.
* Flagged tickets remain in `status = open`, but are not routed until Admin review.

### 4.2. Auto Routing Engine

* LLM reads `title` and `description` and assigns `department` = `IT` or `HR`. No confidence field; routing is mandatory.
* System sets `status = assigned` and `assignee_id` = single agent in that department.
* Agents can change `department` only while `status = open` (rare manual override).

### 4.3. Response Suggestion (Agent Side)

* Agent clicks “Reply with AI” within ticket conversation.
* Backend uses central knowledge base (RAG) to draft a response.
* Suggested response returned as text; agent can edit and send.
* Suggested messages have `isAI = true`.

### 4.4. Self-Serve Answer Bot (User Side)

* Hosted on user homepage.
* Users can ask questions; backend returns responses from central knowledge base.
* Maintains short context (last 3 queries) for session continuity.
* Self-serve responses have `isAI = true`.

### 4.5. Misuse Pattern Detector (Admin Tool)

* Runs daily or on demand.
* Aggregates each user’s tickets over past 24h or 7d.
* Uses LLM to detect:

  * Duplicate or repetitive tickets
  * Spammy or meaningless content
  * Abusive language or jailbreaking attempts
* Creates entries in `misuse_reports` collection with:

  * `user_id`, `detection_date`, `misuse_type`, `severity_level`, `evidence_data`, `admin_reviewed`, `action_taken`, `ai_analysis_metadata`.
* Admin dashboard displays flagged users, reasons, and allows marking `admin_reviewed = true`.

---

## 5. Soft Rate Limiting

* Limit: 5 tickets per user per 24 hours.
* On ticket creation, count user’s tickets where `created_at >= now() - 24h`.
* If count >= 5, reject new ticket with error.
* Implemented with a MongoDB `count_documents` query.

---

## 6. Webhook-Based Internal Notifications

### Events:

* **on\_ticket\_created**: Fires when ticket leaves HSA check & routing assigns department.
* **on\_message\_sent**: Fires on every new chat message.
* **on\_ai\_reply\_suggested**: Fires when AI draft is generated.
* **on\_ticket\_resolved**: Fires when user marks ticket `resolved`.
* **on\_ticket\_closed**: Fires when agent marks ticket `closed`.
* **on\_misuse\_detected**: Fires when misuse pattern detector flags a user.

### Webhook Mechanics:

* Internal FastAPI handlers (no external services).
* Each event hits a `/internal/webhook/<event_name>` endpoint.
* Retry logic on failure (exponential backoff).

---

## 7. Database Schema (MongoDB)

### 7.1. users Collection

```
users: {
  _id: ObjectId,
  username: String (Unique),
  email: String (Unique),
  password_hash: String,
  role: String (Enum: "user", "it_agent", "hr_agent", "admin"),
  created_at: DateTime,
  updated_at: DateTime,
  is_active: Boolean,
  last_login: DateTime,
  rate_limit_reset: DateTime
}
```

### 7.2. tickets Collection

```
tickets: {
  _id: ObjectId,
  ticket_id: String (Unique),
  title: String,
  description: String,
  urgency: String (Enum: "low", "medium", "high"),
  status: String (Enum: "open", "assigned", "resolved", "closed"),
  department: String (Enum: "IT", "HR"),
  assignee_id: ObjectId or null,
  user_id: ObjectId,
  created_at: DateTime,
  updated_at: DateTime,
  closed_at: DateTime or null,
  misuse_flag: Boolean,
  feedback: String or null
}
```

### 7.3. messages Collection

```
messages: {
  _id: ObjectId,
  ticket_id: ObjectId,
  sender_id: ObjectId,
  sender_role: String (Enum: "user", "it_agent", "hr_agent", "admin"),
  message_type: String (Enum: "user_message", "agent_message", "system_message"),
  content: String,
  isAI: Boolean,
  feedback: String (Enum: "up", "down", "none"),
  timestamp: DateTime
}
```

### 7.4. misuse\_reports Collection

```
misuse_reports: {
  _id: ObjectId,
  user_id: ObjectId,
  detection_date: DateTime,
  misuse_type: String (Enum: "duplicate_tickets", "spam_content", "abusive_language", "jailbreak_attempt"),
  severity_level: String (Enum: "low", "medium", "high"),
  evidence_data: {
    ticket_ids: Array[ObjectId],
    content_samples: Array[String],
    pattern_analysis: String
  },
  admin_reviewed: Boolean,
  action_taken: String or null,
  ai_analysis_metadata: {
    detection_confidence: Float,
    model_reasoning: String,
    analysis_timestamp: DateTime
  }
}
```

### 7.5. knowledge\_base Collection

```
knowledge_base: {
  _id: ObjectId,
  document_id: String (Unique),
  title: String,
  content: String,
  category: String (Enum: "IT", "HR", "General"),
  tags: Array[String],
  created_at: DateTime,
  updated_at: DateTime,
  usage_count: Integer,
  effectiveness_score: Float
}
```

---

## 8. API Endpoints

### 8.1. Authentication

```
POST /auth/login
- Request: {"username": String, "password": String}
- Response: {"access_token": String, "token_type": "bearer", "user": {user object}}
- Process: Validate credentials → Issue JWT

POST /auth/logout
- Headers: Authorization: Bearer <token>
- Response: {"message": "Logout successful"}
- Process: Invalidate JWT → Cleanup session

GET /auth/me
- Headers: Authorization: Bearer <token>
- Response: {user object without password_hash}
- Process: Decode JWT → Fetch user
```

### 8.2. Ticket Endpoints

```
POST /tickets
- Headers: Authorization: Bearer <token>
- Request: {"title": String, "description": String, "urgency"?: String}
- Response: Ticket object
- Process:
  1. Rate limit check (5 tickets/24h)
  2. HSA validation → If flagged, set misuse_flag and notify Admin → return ticket in open state
  3. LLM routing → Set department and assignee_id, status = assigned
  4. Save to DB → Return ticket
  5. Fire on_ticket_created webhook

GET /tickets
- Headers: Authorization: Bearer <token>
- Query Params: status, department, page, limit
- Response: {tickets: Array[Ticket], total_count, pagination}
- Process: Role-based filtering → Paginated DB query

GET /tickets/{ticket_id}
- Headers: Authorization: Bearer <token>
- Response: Ticket object including messages
- Process: Validate access → Fetch ticket → Populate messages

PUT /tickets/{ticket_id}
- Headers: Authorization: Bearer <token>
- Request: {"title"?: String, "description"?: String, "status"?: String, "department"?: String}
- Response: Updated ticket object
- Process:
  - If editing title/description: ensure ticket `status = open` and user is owner
  - If changing department: ensure `status = open` and user or agent
  - If changing status: enforce sequence (open → assigned → resolved → closed) and correct roles
  - Update DB → Fire appropriate webhook

POST /tickets/{ticket_id}/messages
- Headers: Authorization: Bearer <token>
- Request: {"content": String, "message_type": String, "isAI": Boolean}
- Response: Message object
- Process: Validate access → Save message → Broadcast via WebSocket → Fire on_message_sent webhook

POST /tickets/{ticket_id}/resolve
- Headers: Authorization: Bearer <token>
- Response: {"message": "Ticket marked as resolved"}
- Process: Only user can hit this → Set status = resolved → Fire on_ticket_resolved webhook

POST /tickets/{ticket_id}/close
- Headers: Authorization: Bearer <token>
- Response: {"message": "Ticket closed"}
- Process: Only agent can hit this when status = resolved → Set status = closed, set closed_at → Fire on_ticket_closed webhook
```

### 8.3. AI Endpoints

```
POST /ai/suggest-response
- Headers: Authorization: Bearer <token>
- Request: {"ticket_id": String, "conversation_context": Array[Message]}
- Response: {"suggested_response": String}
- Process: Agent validation → RAG query to knowledge_base → Generate draft → Return with isAI = true → Fire on_ai_reply_suggested webhook

POST /ai/self-serve-query
- Request: {"query": String, "session_id"?: String}
- Response: {"answer": String}
- Process: RAG query to knowledge_base → Return answer with isAI = true
```

### 8.4. Admin Endpoints

```
GET /admin/misuse-reports
- Headers: Authorization: Bearer <token>
- Response: Array of misuse_report objects
- Process: Admin validation → Fetch all reports (filtered by reviewed if needed)

POST /admin/mark-reviewed
- Headers: Authorization: Bearer <token>
- Request: {"report_id": String}
- Response: {"message": "Marked as reviewed"}
- Process: Admin validation → Set admin_reviewed = true → Update action_taken if provided
```

---

## 9. Error Handling and Debugging Framework

### 9.1. Error Response Structure

```
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable description",
    "details": "Technical details (if any)",
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

* `AUTH_INVALID`: Authentication failed.
* `AUTHZ_FORBIDDEN`: Role not allowed.
* `VALIDATION_ERROR`: Input validation failed.
* `RATE_LIMIT_EXCEEDED`: Ticket creation limit reached.
* `AI_PROCESSING_ERROR`: Error invoking AI module.
* `DB_ERROR`: Database operation failed.
* `WS_ERROR`: WebSocket broadcast failure.

### 9.2. Logging Strategy

* **Structured Logs** (JSON format) with fields:

  * `timestamp`: ISO 8601
  * `level`: `DEBUG`, `INFO`, `WARN`, `ERROR`
  * `service`: "helpdesk-api"
  * `module`: e.g., `ticket_service`, `auth_service`, `ai_service`
  * `user_id`: ID of acting user (if any)
  * `request_id`: Unique identifier per request
  * `event`: Short description
  * `data`: Additional contextual info
  * `duration_ms`: Time taken to process request

* **Retention:**

  * `ERROR` logs: 90 days
  * `WARN` logs: 30 days
  * `INFO` logs: 7 days
  * `DEBUG` logs: 1 day

---

*This document includes all changes requested: simplified AI routing (no confidence), ticket status lifecycle updates, message attributes for AI origin and feedback, removal of escalation/reassignment, and a focused debugging section.*
