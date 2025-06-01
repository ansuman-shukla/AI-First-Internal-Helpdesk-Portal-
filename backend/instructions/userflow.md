USER JOURNEY (Role: user)

Login

UI Action: User enters username and password.

API Call: POST /auth/login

Logic:

Validate credentials.

Return JWT token.

Raise a Ticket

UI Action: User clicks "New Ticket" and fills in title, description, urgency.

API Call: POST /tickets

Logic:

Rate Limit Check: Count tickets created by this user in the last 24h. If ≥5, reject with RATE_LIMIT_EXCEEDED.

HSA Check: Call HSA LLM module. If is_harmful == true, set misuse_flag=true, notify Admin, and return ticket with status="open" (no routing).

Auto Routing: Call routing engine with { title, description }. Receive department (IT or HR). (Removed confidence; routing is deterministic.)

Ticket Creation: Save ticket with fields:

status = "assigned" (immediately assigned)

department (from routing)

assignee_id = the sole agent in that department

user_id = current user

misuse_flag as determined

created_at, updated_at

Trigger: Fire POST /internal/webhook/on_ticket_created.

Changes from Draft: Removed routing confidence. Endpoint corrected to /tickets.

View Ticket List

UI Action: User goes to "My Tickets" page.

API Call: GET /tickets?user_id=<current_user>&status=&department=&page=&limit=(Note: FastAPI dependency auto-filters by user_id so GET /tickets returns only this user’s tickets, with optional query parameters.)

Logic: Return paginated list of tickets created by the user.

Changes from Draft: Changed endpoint to GET /tickets with filters; removed /ticket/my.

Open Ticket Chat

UI Action: User clicks on a ticket to view messages.

API Calls:

GET /tickets/{ticket_id}  → Returns ticket object + conversation (messages).

WebSocket Connect: /ws/chat/{ticket_id}

Logic:

Validate user access: ensure ticket.user_id == current_user.

Load message history from messages collection.

Send Message

UI Action: User types and sends a message.

WebSocket Message Payload:

{
  "type": "chat",
  "ticket_id": "<ticket_id>",
  "sender_id": "<user_id>",
  "sender_role": "user",
  "content": "My laptop won’t turn on",
  "isAI": false,
  "feedback": "none"
}

Logic:

Validate user belongs to ticket.

Save message to messages with sender_role="user", isAI=false, feedback="none", timestamp.

Broadcast via WebSocket to room ticket_<ticket_id>.

Trigger: POST /internal/webhook/on_message_sent.

Query Self-Serve Bot

UI Action: User types question in homepage bot input.

API Call: POST /ai/self-serve-queryRequest: { "query": "<user_question>", "session_id": "<optional>" }

Logic:

Perform RAG query over knowledge_base.

Return LLM-generated answer text with isAI=true.

No Changes.

Mark Ticket as Resolved (Optional)

UI Action: User clicks "Mark Resolved" and optionally adds feedback.

API Call: POST /tickets/{ticket_id}/resolve

Logic:

Validate user owns the ticket and status == "assigned" or "open".

Set status = "resolved", store feedback if provided.

Update updated_at.

Trigger: POST /internal/webhook/on_ticket_resolved.

Note: After user resolves, only an agent can close.

Changes from Draft: Split into dedicated /resolve endpoint; user cannot directly close—must use /resolve first.

