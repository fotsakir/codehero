# Plan: Auto Review System for Relaxed Mode

## Overview
Implement an intelligent auto-review system that uses Haiku to determine if a ticket is truly completed or needs user input before progressing to the next ticket.

---

## Phase 1: Database Changes

### 1.1 Add `awaiting_reason` column to tickets
```sql
ALTER TABLE tickets ADD COLUMN awaiting_reason
  ENUM('completed', 'question', 'error', 'stopped', 'permission', 'deps_ready')
  DEFAULT NULL;
```

### 1.2 Add `review_scheduled_at` column for 15-minute delay
```sql
ALTER TABLE tickets ADD COLUMN review_scheduled_at DATETIME DEFAULT NULL;
```

### 1.3 Create migration file
- File: `database/migrations/2.72.0_auto_review_system.sql`

---

## Phase 2: Haiku Classification Service

### 2.1 Add Anthropic API call in daemon
```python
def classify_completion(self, ticket_id: int) -> str:
    """
    Use Haiku to classify if ticket is completed or needs input.
    Returns: 'COMPLETED', 'QUESTION', or 'ERROR'
    """
    # Get last user message
    last_user_msg = self.get_last_user_message(ticket_id)

    # Get all assistant messages after last user message
    ai_messages = self.get_messages_after(ticket_id, last_user_msg['created_at'], role='assistant')

    if not ai_messages:
        return 'ERROR'

    # Build prompt for Haiku
    prompt = f"""Analyze this AI assistant conversation and classify the outcome.

User's Request:
{last_user_msg['content'][:1000]}

AI's Response:
{self.format_messages(ai_messages)[-3000:]}

Based on the AI's response, classify as:
- COMPLETED - The AI finished the task successfully and is reporting completion
- QUESTION - The AI is asking the user a question and waiting for response
- ERROR - The AI encountered a problem it cannot solve alone

Reply with ONLY one word: COMPLETED, QUESTION, or ERROR"""

    response = anthropic.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=10,
        messages=[{"role": "user", "content": prompt}]
    )

    result = response.content[0].text.strip().upper()
    return result if result in ['COMPLETED', 'QUESTION', 'ERROR'] else 'QUESTION'
```

### 2.2 Helper functions needed
```python
def get_last_user_message(self, ticket_id: int) -> dict:
    """Get the most recent user message for a ticket."""

def get_messages_after(self, ticket_id: int, after_time: datetime, role: str = None) -> list:
    """Get all messages after a specific timestamp, optionally filtered by role."""

def get_last_message_role(self, ticket_id: int) -> str:
    """Get the role of the most recent message (user/assistant/system)."""
```

---

## Phase 3: Review Scheduler

### 3.1 When Claude exits (in process_ticket)
```python
# Current code at line ~1506
# BEFORE:
self.update_ticket(ticket['id'], 'awaiting_input')

# AFTER:
# Schedule review for 15 minutes later
cursor.execute("""
    UPDATE tickets SET
        status = 'awaiting_input',
        review_scheduled_at = DATE_ADD(NOW(), INTERVAL 15 MINUTE)
    WHERE id = %s
""", (ticket['id'],))
self.log(f"Scheduled review for {ticket['ticket_number']} in 15 minutes")
```

### 3.2 New background job: process_scheduled_reviews()
```python
def process_scheduled_reviews(self):
    """Process tickets that are due for review."""

    cursor.execute("""
        SELECT t.id, t.ticket_number, t.deps_include_awaiting
        FROM tickets t
        WHERE t.status = 'awaiting_input'
          AND t.review_scheduled_at IS NOT NULL
          AND t.review_scheduled_at <= NOW()
          AND t.awaiting_reason IS NULL
    """)

    for ticket in cursor.fetchall():
        # Check last message role
        last_role = self.get_last_message_role(ticket['id'])

        if last_role != 'assistant':
            # Last message not from AI - skip review
            # Clear the scheduled review
            cursor.execute("""
                UPDATE tickets SET review_scheduled_at = NULL
                WHERE id = %s
            """, (ticket['id'],))
            continue

        # Only do auto-review for relaxed mode tickets
        if not ticket['deps_include_awaiting']:
            # Strict mode - don't auto-close
            cursor.execute("""
                UPDATE tickets SET
                    review_scheduled_at = NULL,
                    awaiting_reason = 'completed'
                WHERE id = %s
            """, (ticket['id'],))
            continue

        # Do Haiku classification
        result = self.classify_completion(ticket['id'])

        if result == 'COMPLETED':
            # Auto-close ticket
            cursor.execute("""
                UPDATE tickets SET
                    status = 'done',
                    awaiting_reason = NULL,
                    review_scheduled_at = NULL,
                    close_reason = 'auto_reviewed',
                    updated_at = NOW()
                WHERE id = %s
            """, (ticket['id'],))
            self.log(f"Auto-closed {ticket['ticket_number']} (Haiku: COMPLETED)")
        else:
            # Stay in awaiting_input with reason
            cursor.execute("""
                UPDATE tickets SET
                    awaiting_reason = %s,
                    review_scheduled_at = NULL
                WHERE id = %s
            """, (result.lower(), ticket['id']))
            self.log(f"Ticket {ticket['ticket_number']} needs input (Haiku: {result})")
```

### 3.3 Add to daemon main loop
```python
def run(self):
    while self.running:
        # Existing ticket processing...

        # Add: Check for scheduled reviews every cycle
        self.process_scheduled_reviews()
```

---

## Phase 4: Kill Switch Update

### 4.1 Update MCP kill_switch handler
```python
# In handle_kill_switch(), change:
cursor.execute("""
    UPDATE tickets SET
        status = 'awaiting_input',
        awaiting_reason = 'stopped',      # NEW
        review_scheduled_at = NULL,        # Cancel any pending review
        updated_at = NOW()
    WHERE id = %s
""", (ticket_id,))
```

---

## Phase 5: Cancel Review on User Message

### 5.1 When user sends a message, cancel pending review
```python
# In the message handling code:
cursor.execute("""
    UPDATE tickets SET review_scheduled_at = NULL
    WHERE id = %s AND review_scheduled_at IS NOT NULL
""", (ticket_id,))
```

---

## Phase 6: UI Updates (Optional)

### 6.1 Show awaiting_reason in ticket list
- Display icon/badge based on reason:
  - `completed` → ✅ Ready for review
  - `question` → ❓ AI asking question
  - `error` → ⚠️ Needs attention
  - `stopped` → ⏹️ Manually stopped
  - `permission` → 🔐 Waiting for permission

### 6.2 Show countdown to auto-review
- If `review_scheduled_at` is set, show "Auto-review in X minutes"

---

## Summary Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     TICKET COMPLETES                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Set status = 'awaiting_input'                                  │
│  Set review_scheduled_at = NOW() + 15 minutes                   │
└─────────────────────────────────────────────────────────────────┘
                              │
            ┌─────────────────┴─────────────────┐
            │                                   │
            ▼                                   ▼
┌───────────────────────┐           ┌───────────────────────┐
│  User sends message   │           │  15 minutes pass      │
│  within 15 min        │           │  (no user activity)   │
└───────────────────────┘           └───────────────────────┘
            │                                   │
            ▼                                   ▼
┌───────────────────────┐           ┌───────────────────────┐
│  Cancel review        │           │  Check last message   │
│  review_scheduled_at  │           │  role                 │
│  = NULL               │           └───────────────────────┘
└───────────────────────┘                       │
            │                       ┌───────────┴───────────┐
            ▼                       │                       │
┌───────────────────────┐           ▼                       ▼
│  Continue             │   ┌─────────────┐         ┌─────────────┐
│  conversation         │   │ role=user   │         │ role=assist │
└───────────────────────┘   │ or system   │         │             │
                            └─────────────┘         └─────────────┘
                                    │                       │
                                    ▼                       ▼
                            ┌─────────────┐         ┌─────────────┐
                            │ Skip review │         │ Haiku       │
                            │ Wait for AI │         │ Classification│
                            └─────────────┘         └─────────────┘
                                                            │
                                    ┌───────────────────────┼───────────────────────┐
                                    │                       │                       │
                                    ▼                       ▼                       ▼
                            ┌─────────────┐         ┌─────────────┐         ┌─────────────┐
                            │ COMPLETED   │         │ QUESTION    │         │ ERROR       │
                            └─────────────┘         └─────────────┘         └─────────────┘
                                    │                       │                       │
                                    ▼                       ▼                       ▼
                            ┌─────────────┐         ┌─────────────┐         ┌─────────────┐
                            │ Auto-close  │         │ Stay        │         │ Stay        │
                            │ status=done │         │ awaiting    │         │ awaiting    │
                            │ Next ticket │         │ reason=     │         │ reason=     │
                            │ starts      │         │ 'question'  │         │ 'error'     │
                            └─────────────┘         └─────────────┘         └─────────────┘
```

---

## Files to Modify

1. `database/migrations/2.72.0_auto_review_system.sql` - NEW
2. `scripts/claude-daemon.py` - Add Haiku classification & review scheduler
3. `scripts/mcp_server.py` - Update kill_switch to set awaiting_reason
4. `web/templates/tickets_list.html` - Show awaiting_reason (optional)
5. `web/templates/ticket_detail.html` - Show awaiting_reason (optional)

---

## Version
This will be released as v2.72.0
