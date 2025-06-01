ADMIN JOURNEY (Role: admin)

Login(Same as User Journey.)

View Misuse Reports

UI Action: Admin dashboard shows flagged users/tickets.

API Call: GET /admin/misuse-reports

Logic:

Fetch all docs from misuse_reports where admin_reviewed == false (optional filter).

Investigate a Flag

UI Action: Admin clicks on a report → sees impacted tickets and messages.

API Calls:

GET /tickets/{ticket_id} → Ticket object.

GET /tickets/{ticket_id}/messages → Messages array.

Manually Close Ticket

UI Action: Admin chooses to close a problematic ticket immediately (regardless of status).

API Call: POST /tickets/{ticket_id}/close

Logic:

Validate admin role.

Set status = "closed", set closed_at = now.

Update updated_at.

Trigger: POST /internal/webhook/on_ticket_closed.

Note: Admin cannot reassign or escalate — only close.

Review Topic Clusters (Future Scope)

UI Action: Admin views ticket clustering insights (e.g., top 5 issues).

Backend Logic (Batch Job, not part of current MVP):

Periodically run LLM/embedding clustering over all tickets to identify frequent themes.

Store results in repetitive_themes_reports (out of scope for now).

No Changes. (Future scope only.)
