---
name: telegram-buttons
description: Send interactive inline buttons with Telegram messages. Use when you need to create clickable buttons that trigger callbacks (e.g., confirm/cancel dialogs, calendar selections, quiz options, schedule actions). Supports button styling, custom callback data, and callback pattern routing to n8n webhooks.
---

# Telegram Buttons Skill

Send interactive inline buttons with Telegram messages using the `message` tool.

## Quick Start

Use the `message` tool with the `buttons` parameter:

```javascript
message(
  action='send',
  message='Choose an option:',
  buttons=[[
    { text: 'Confirm', callback_data: 'cc|confirm-action' },
    { text: 'Cancel', callback_data: 'cancel|cancel-action' }
  ]]
)
```

**Result:** Message sent with two clickable buttons. When clicked, the callback_data gets sent to the user's callback handler.

## Button Structure

Each button is a JSON object:

```javascript
{
  text: 'Button Label',           // What shows on the button (required)
  callback_data: 'cc|action-id',  // Data sent when clicked (required)
  style: 'primary'                // Optional: 'primary', 'success', 'danger'
}
```

## Callback Data Patterns

Use these prefixes for callback data to match n8n webhook routing:

| Pattern | Use Case | Example |
|---------|----------|---------|
| `cc\|*` | Calendar confirm | `cc\|confirm-meeting` |
| `cs\|*` | Calendar select | `cs\|select-time` |
| `cancel\|*` | Cancellation | `cancel\|cancel-order` |
| `confirm\|*` | Confirmation | `confirm\|submit-form` |
| `schedule\|*` | Schedule action | `schedule\|book-slot` |
| `edit\|*` | Edit action | `edit\|change-settings` |
| `delete\|*` | Delete action | `delete\|remove-item` |

## Examples

### Confirm/Cancel Dialog

```javascript
message(
  action='send',
  message='Delete this item? (cannot undo)',
  buttons=[[
    { text: '✓ Delete', callback_data: 'confirm|delete-item', style: 'danger' },
    { text: '✕ Cancel', callback_data: 'cancel|cancel-delete', style: 'primary' }
  ]]
)
```

### Calendar Selection

```javascript
message(
  action='send',
  message='Select time slot:',
  buttons=[[
    { text: '9 AM', callback_data: 'cs|slot-09am' },
    { text: '2 PM', callback_data: 'cs|slot-02pm' },
    { text: '5 PM', callback_data: 'cs|slot-05pm' }
  ]]
)
```

### Styled Buttons

```javascript
message(
  action='send',
  message='What would you like to do?',
  buttons=[[
    { text: 'Schedule', callback_data: 'schedule|action', style: 'primary' },
    { text: 'Edit', callback_data: 'edit|action', style: 'primary' },
    { text: 'Delete', callback_data: 'delete|action', style: 'danger' }
  ]]
)
```

### Multiple Rows

```javascript
message(
  action='send',
  message='Options:',
  buttons=[
    [
      { text: 'Yes', callback_data: 'confirm|yes' },
      { text: 'No', callback_data: 'cancel|no' }
    ],
    [
      { text: 'Maybe', callback_data: 'cs|maybe' }
    ]
  ]
)
```

Each inner array is a row; buttons in the same array appear side-by-side.

## Callback Flow

1. User clicks button
2. Telegram sends callback to OpenClaw
3. SOUL.md callback handler routes based on pattern:
   - **Known patterns** (cc|, cs|, cancel|, etc.) → Forward to n8n webhook
   - **Unknown patterns** → Pass through normally
4. Webhook processes the action

## Common Patterns

### Quiz/Poll

```javascript
message(
  action='send',
  message='What is 2+2?',
  buttons=[[
    { text: '3', callback_data: 'quiz|q1-wrong' },
    { text: '4', callback_data: 'quiz|q1-correct', style: 'success' },
    { text: '5', callback_data: 'quiz|q1-wrong' }
  ]]
)
```

### Booking

```javascript
message(
  action='send',
  message='Book appointment:',
  buttons=[[
    { text: 'Monday 10 AM', callback_data: 'schedule|mon-10am' },
    { text: 'Tuesday 2 PM', callback_data: 'schedule|tue-02pm' },
    { text: 'Wednesday 4 PM', callback_data: 'schedule|wed-04pm' }
  ]]
)
```

## Troubleshooting

**Buttons not appearing?**
- Check button syntax (text, callback_data are required)
- Verify buttons array structure: `buttons=[[{...}, {...}]]` (double brackets)
- Ensure message text is not empty

**Callbacks not reaching webhook?**
- Check callback_data format matches expected pattern (cc|, cs|, etc.)
- Verify n8n webhook URL is correct in SOUL.md
- Check Telegram bot token configuration

**Wrong styling?**
- Valid styles: `primary`, `success`, `danger`
- Default (no style) is neutral gray

## Notes

- Button labels are limited to ~20 characters
- Max 5 buttons per row recommended (Telegram UI limits)
- callback_data max ~60 characters
- Each button triggers one callback per click
