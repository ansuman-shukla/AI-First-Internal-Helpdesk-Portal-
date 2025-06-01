AGENT JOURNEY (Role: it_agent or hr_agent)

Login(Same as User Journey.)

View Assigned Tickets

UI Action: Agent dashboard shows tickets in their department.

API Call: GET /tickets?department=<"IT"|"HR">&status=assigned(FastAPI filters by role → agent only sees tickets assigned to them or their department.)

Logic: Return paginated list of tickets where department == agent.department and status == "assigned".

Changes from Draft: Clarified endpoint filters; removed /ticket/my.

Open Ticket Chat(Same as User: GET /tickets/{ticket_id} + WebSocket connect to `/ws/chat/{ticket_id}.)

Receive Message

WebSocket Event: New message broadcast from user or AI.

UI Logic: Display in real time in chat window.

Request AI Reply Suggestion

UI Action: Agent clicks "Suggest Reply" button.

API Call: POST /ai/suggest-response
Request:

{
  "ticket_id": "<ticket_id>",
  "conversation_context": [ <last  few messages> ]
}

Logic:

Validate agent assigned to this ticket.

Call RAG LLM module using knowledge_base + conversation_context.

Return { "suggested_response": "<AI text>" } with isAI=true.

Fire POST /internal/webhook/on_ai_reply_suggested.

No Routing Confidence; suggestion is delivered directly.

Send Message

UI Action: Agent types and sends a message manually.

WebSocket Payload:

{
  "type": "chat",
  "ticket_id": "<ticket_id>",
  "sender_id": "<agent_id>",
  "sender_role": "it_agent" or "hr_agent",
  "content": "<agent_text>",
  "isAI": false,
  "feedback": "none"
}

Logic:

Save to messages collection.

Broadcast to ticket_<ticket_id> room.

Trigger POST /internal/webhook/on_message_sent.

Send AI-Generated Reply

UI Action: Agent reviews AI suggestion, optionally edits, then clicks "Send AI Reply".

WebSocket Payload:

{
  "type": "chat",
  "ticket_id": "<ticket_id>",
  "sender_id": "<agent_id>",
  "sender_role": "it_agent" or "hr_agent",
  "content": "<edited_or_original_suggestion>",
  "isAI": true,
  "feedback": "none"
}

Logic:

Save to messages with isAI=true.

Broadcast via WebSocket.

Agents can later update feedback on AI message (up/down).

Trigger POST /internal/webhook/on_message_sent.

Mark Ticket as Closed (Agent)

UI Action: Agent clicks "Close Ticket" when they see status == "resolved".

API Call: POST /tickets/{ticket_id}/close

Logic:

Validate agent assigned to this ticket and current status == "resolved".

Set status = "closed", set closed_at = now.

Update updated_at.

Trigger: POST /internal/webhook/on_ticket_closed.

Changes from Draft: Removed agent ability to close until after a user has resolved; used dedicated /close endpoint.
