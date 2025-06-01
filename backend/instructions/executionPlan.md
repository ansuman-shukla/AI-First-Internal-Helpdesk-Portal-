**Development Plan: Modular Phases for Helpdesk System (Validated & Updated)**

---

## Overview:

To avoid overwhelm and ensure focused, rapid development, the project will be built in clear modular phases. Each phase builds on the previous one and only includes the minimum features needed for that step.

---

## Phase 0: Project Setup (Boilerplate)

### Goals:

Set up a clean, minimal project structure to support modular growth.

### Tasks:

* Initialize FastAPI project
* Create folder structure:

  * `app/`

    * `routers/`
    * `models/`
    * `schemas/`
    * `services/`
    * `utils/`
    * `core/`
  * `tests/`
  * `main.py`
* Set up MongoDB connection
* Add user auth logic (login, session, role-based access)
* Basic homepage for each role (User, Agent, Admin) with placeholder text

---

## Phase 1: Ticket Management System (Backbone)

### Goals:

Build the core functionality for ticket creation, viewing, and editing.

### Tasks:

* **User can:**

  * Create a ticket (title, description, urgency)
  * Edit own tickets (not delete)
  * View list of tickets
* **System stores:**

  * Ticket metadata (status, timestamps)
  * Which user submitted the ticket
* **Admin and Agent can:**

  * View all tickets
  * See ticket details
* No AI logic in this phase
* No real-time chat yet

---

## Phase 2: LLM Auto-Routing & HSA Filtering

### Goals:

Implement LLM-based routing and harmful/spam content filtering.

### Tasks:

* When user submits ticket:

  1. Run HSA check (LLM): block if harmful
  2. Run Routing Engine (LLM): auto-categorize to IT or HR (deterministic, no confidence score)
  3. Assign to correct agent based on department
* Notify admin if harmful content detected

> **Update:** Removed flagging for low-confidence routing, as routing is now deterministic per PRD.

---

## Phase 3: Self-Serve AI Bot (Homepage)

### Goals:

Allow user to interact with knowledge-based bot to reduce ticket load.

### Tasks:

* Add simple chat interface on homepage
* Backend calls RAG LLM with context
* Show reply from AI to user
* Track last 3 messages for short context memory (session only)

---

## Phase 4: Real-Time Chat Inside Ticket

### Goals:

Enable live 1-on-1 messaging between agent and user in each ticket.

### Tasks:

* Integrate WebSocket (FastAPI’s built-in support)
* Create chat interface within ticket view
* Store messages in `messages` collection
* Enable notification on new message via webhook

---

## Phase 5: Agent-Side AI Suggestions

### Goals:

Boost agent productivity with AI-powered response suggestions.

### Tasks:

* Add **"Reply with AI"** button for agents
* Call RAG LLM using central knowledge base + ticket context
* Suggest response draft
* Agent can edit or send as-is

---

## Phase 6: Admin Panel & Misuse Detection

### Goals:

Let admin monitor system misuse and intervene.

### Tasks:

* Show list of misuse reports in admin dashboard
* Allow admin to see flagged users & reasons
* Implement Misuse Detector (LLM) that runs daily or on ticket-creation events:

  * Detect repeated abuse/spam/jailbreak attempts
  * Populate `misuse_reports` collection
* Enable admin to close tickets if needed

---

## Phase 7 (Optional): Soft Rate Limiting

### Goals:

Prevent ticket spam.

### Tasks:

* Track number of tickets created by each user in past 24 hours
* Show warning after 5 tickets
* Block submission temporarily when limit reached

---

*This plan is now fully aligned with the PRD. The only change made was removing low-confidence routing flagging in Phase 2 to match deterministic routing per product requirements.*
