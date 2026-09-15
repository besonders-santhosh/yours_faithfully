# AeroTrace — Ambient Cursor Co-Pilot

**Version:** 1.0  
**Project Type:** 3-Hour Hackathon MVP  
**Theme:** "Agents are leaving the chatbox. Build an agent for a place people already work, talk, or live."

---

## 1. Product Overview

### Product Name

**AeroTrace — Ambient Cursor Co-Pilot**

### One-Line Description

> AeroTrace is a desktop AI agent that understands what's underneath your cursor and gives help directly beside it — without opening a chatbox.

### Problem

Today's AI assistants usually require users to:

1. Stop what they are doing.
2. Open an AI chat.
3. Explain what they are looking at.
4. Copy and paste relevant information.
5. Wait for an answer.
6. Return to their original application.

This creates unnecessary friction.

When a developer encounters an error, for example, they should not have to copy the error into an AI chatbot just to ask what it means.

### Solution

AeroTrace brings AI into the user's existing workspace.

The user simply moves their mouse over something interesting or confusing.

AeroTrace:

1. Detects where the cursor is.
2. Captures a small region around it.
3. Extracts visible text using OCR.
4. Sends the context to an AI reasoning agent.
5. Determines what the user is looking at.
6. Generates a concise explanation or suggested action.
7. Displays the result beside the cursor.

There is **no chatbox**.

---

# 2. Hackathon Goal

Build a convincing working prototype in approximately **3 hours** demonstrating that an AI agent can operate directly inside an existing desktop workflow.

The MVP should prove one core interaction:

> **Cursor → Context → AI Agent → Immediate Help**

The project does NOT need to become a fully featured desktop assistant.

The goal is a reliable and impressive demonstration of the concept.

---

# 3. Target User

### Primary User

Developers, students, and technical users working on a desktop.

### Example Scenario

A developer sees:

```text
ModuleNotFoundError: No module named 'requests'
```

Instead of copying the error into an AI chatbot, the user simply hovers over it.

AeroTrace responds:

```text
AeroTrace

Problem:
Python cannot find the requests package.

Fix:
Run:

pip install requests
```

The user continues working without leaving their terminal.

---

# 4. Core User Experience

## Normal Interaction

```text
User works normally
        ↓
Moves cursor over content
        ↓
Cursor stays still for ~800 ms
        ↓
AeroTrace detects dwell
        ↓
Capture screen region
        ↓
OCR extracts text
        ↓
AI analyzes context
        ↓
HUD appears beside cursor
        ↓
User receives help
```

## Manual Interaction

A keyboard shortcut provides a reliable backup:

```text
Ctrl + Shift + Space
        ↓
Capture current cursor context
        ↓
Analyze
        ↓
Show HUD
```

---

# 5. MVP Features

## P0 — Must Have

### 5.1 Cursor Dwell Detection

AeroTrace monitors the mouse position.

If the cursor remains approximately stationary for:

```text
800 milliseconds
```

AeroTrace triggers an analysis.

Technology:

- `pynput`

---

### 5.2 Screen Context Capture

Capture a small region around the cursor.

Target size:

```text
400 × 250 pixels
```

For cursor coordinates `(X, Y)`:

```text
left   = X - 200
top    = Y - 125
width  = 400
height = 250
```

Clamp coordinates so they do not go outside the screen.

Technology:

- `mss`
- `numpy`

---

### 5.3 OCR

Extract visible text from the captured screen region.

Initial implementation:

- `easyocr`

Example:

```text
ModuleNotFoundError:
No module named 'requests'
```

OCR output:

```text
ModuleNotFoundError: No module named 'requests'
```

OCR failure must not crash the application.

---

### 5.4 AI Context Analysis

The extracted text is sent to an AI model.

The model determines:

- Whether the content represents a technical issue.
- What the issue means.
- What the likely solution is.
- Whether clarification is required.

The response must use structured output.

### Data Model

```python
class ErrorAnalysis(BaseModel):
    is_technical_issue: bool
    confidence_score: float
    issue_summary: str
    suggested_fix: str
    clarification_question: str | None
```

Example:

```json
{
  "is_technical_issue": true,
  "confidence_score": 0.96,
  "issue_summary": "The Python requests package is not installed.",
  "suggested_fix": "Run pip install requests.",
  "clarification_question": null
}
```

---

### 5.5 Agent Orchestration

Use LangGraph to organize the processing pipeline.

MVP graph:

```text
START
  ↓
Capture Context
  ↓
Extract Text
  ↓
Analyze Context
  ↓
Generate Response
  ↓
Display HUD
  ↓
END
```

The graph should remain intentionally simple.

The purpose of LangGraph is to demonstrate an agent workflow, not unnecessary complexity.

---

### 5.6 Floating HUD

The answer appears directly beside the cursor.

Requirements:

- Borderless window.
- Small footprint.
- Appears near cursor.
- Stays above other windows.
- Does not require opening a chat application.
- Automatically disappears after a short period.
- Should not prevent the user from continuing to work.

Technology:

- `tkinter`

Suggested position:

```text
HUD_X = cursor_x + 20
HUD_Y = cursor_y + 20
```

If the HUD would go outside the screen, reposition it automatically.

---

# 6. Bonus Features

These are **P1** and should only be implemented after the core MVP works.

## 6.1 Voice Input

User can say:

> "What's wrong here?"

AeroTrace combines:

```text
Screen Context
      +
Voice Command
      ↓
     Agent
      ↓
    Answer
```

Technology:

- `sounddevice`
- `faster-whisper`

Target:

- 3-second audio recording
- `tiny.en` model

---

## 6.2 Multimodal Vision

Instead of OCR-only analysis, a multimodal model can inspect the screenshot directly.

Potential capabilities:

- Images.
- UI elements.
- Error messages.
- Buttons.
- Tables.
- Visual indicators.

This is **not required for the initial MVP**.

---

## 6.3 Smart Trigger Filtering

AeroTrace should avoid analyzing every cursor movement.

```text
Cursor moved
     ↓
Wait 800 ms
     ↓
Is cursor still in same area?
     ↓
YES → analyze
NO  → ignore
```

Additional filtering can prevent repeated analysis of the same region.

---

# 7. Technical Architecture

```text
┌───────────────────────────────────────────┐
│                Desktop                    │
│                                           │
│  ┌─────────────┐       ┌──────────────┐  │
│  │    Mouse    │       │ Screen       │  │
│  │   Tracker   │       │ Capture      │  │
│  │  (pynput)   │       │   (mss)      │  │
│  └──────┬──────┘       └──────┬───────┘  │
│         │                     │          │
│         └──────────┬──────────┘          │
│                    ↓                     │
│             Context Pipeline             │
│                    ↓                     │
│              OCR / Vision                │
│            (EasyOCR / VLM)               │
│                    ↓                     │
│              LangGraph Agent             │
│                    ↓                     │
│             Structured Output             │
│               (Pydantic)                 │
│                    ↓                     │
│             Floating HUD                 │
│              (Tkinter)                   │
│                    ↓                     │
│             User continues               │
│                working                  │
└───────────────────────────────────────────┘
```

---

# 8. Software Stack

| Component | Technology |
|---|---|
| Language | Python 3.10+ |
| Mouse tracking | `pynput` |
| Screen capture | `mss` |
| Image processing | `numpy` |
| OCR | `easyocr` |
| Agent orchestration | `langgraph` |
| LLM interface | `langchain-core` / provider SDK |
| Structured output | `pydantic` |
| Voice capture | `sounddevice` |
| Speech-to-text | `faster-whisper` |
| Desktop UI | `tkinter` |
| Notifications | Optional `plyer` |

---

# 9. Project Structure

Recommended:

```text
aerotrace/
│
├── main.py
├── config.py
├── requirements.txt
├── README.md
├── prd.md
│
├── agent/
│   ├── __init__.py
│   ├── graph.py
│   ├── models.py
│   └── prompts.py
│
├── capture/
│   ├── __init__.py
│   ├── mouse.py
│   └── screen.py
│
├── vision/
│   ├── __init__.py
│   └── ocr.py
│
├── voice/
│   ├── __init__.py
│   └── transcription.py
│
└── ui/
    ├── __init__.py
    └── hud.py
```

For the hackathon, fewer files are acceptable if that makes development faster.

---

# 10. Agent State

Suggested LangGraph state:

```python
class AgentState(TypedDict):
    cursor_x: int
    cursor_y: int
    screenshot: object
    extracted_text: str
    voice_text: str | None
    analysis: ErrorAnalysis | None
```

Pipeline:

```text
cursor_x
cursor_y
   ↓
screenshot
   ↓
extracted_text
   +
voice_text
   ↓
analysis
   ↓
HUD
```

---

# 11. AI Prompt Requirements

The AI should behave like an ambient desktop assistant.

It should:

1. Analyze only the available context.
2. Avoid inventing information.
3. Be concise.
4. Prefer actionable fixes.
5. Clearly indicate uncertainty.
6. Ask a clarification question when necessary.
7. Avoid unnecessary explanations.

Suggested system instruction:

```text
You are AeroTrace, an ambient desktop co-pilot.

You receive text extracted from the region underneath the user's
mouse cursor.

Determine whether the content represents a technical issue.

If it is a technical issue:
- Identify the likely problem.
- Explain it briefly.
- Give the most useful next action.

If the evidence is insufficient:
- Do not invent an answer.
- Ask a concise clarification question.

Keep responses short because they will be displayed in a
small floating HUD beside the user's cursor.
```

---

# 12. Trigger Logic

Pseudo-code:

```python
on_mouse_move(x, y):

    if position_changed:
        reset_timer()

    start_timer(800ms)

    if cursor_is_still:
        trigger_analysis(x, y)
```

Important:

- Do not run multiple analyses simultaneously.
- Ignore tiny cursor movements where practical.
- Add a cooldown after an analysis.

Suggested cooldown:

```text
1–2 seconds
```

---

# 13. Error Handling

The application must remain running when individual components fail.

### OCR failure

Display:

```text
I couldn't read the text here.
Try Ctrl+Shift+Space after moving the cursor.
```

### AI failure

Display:

```text
AeroTrace couldn't analyze this context.
```

### Microphone failure

Disable voice functionality but keep screen analysis working.

### API/network failure

The application should not crash.

---

# 14. Privacy Principle

AeroTrace captures screen content only when triggered.

The MVP should **not continuously record the entire screen**.

Capture should be limited to:

```text
small region
+
short duration
+
triggered analysis
```

The application should avoid storing screenshots or audio unless required for debugging.

---

# 15. Performance Requirements

| Metric | Target |
|---|---:|
| Mouse dwell detection | ~800 ms |
| Screen capture | <100 ms |
| OCR | <2–3 sec |
| AI response | <5 sec |
| HUD appearance | Immediately after result |
| Voice recording | ~3 sec |

These are targets, not strict production requirements.

---

# 16. Three-Hour Development Plan

## 0:00–0:20 — Environment

Install and verify:

```text
Python
pynput
mss
numpy
easyocr
langgraph
langchain-core
pydantic
```

Verify the existing skeleton starts.

---

## 0:20–0:50 — Cursor + Screen

Implement:

```text
Mouse tracking
     ↓
Dwell detection
     ↓
Screen capture
```

Test screenshots.

---

## 0:50–1:20 — OCR

Implement:

```text
Screenshot
    ↓
EasyOCR
    ↓
Extracted text
```

Test with terminal errors, browser text, and code editor errors.

---

## 1:20–2:00 — AI Agent

Replace mock analysis with a real LLM call.

Implement:

```text
OCR text
   ↓
Prompt
   ↓
Structured AI response
   ↓
ErrorAnalysis
```

Test with 3–5 different errors.

---

## 2:00–2:30 — HUD

Build the floating Tkinter window.

Test that it appears next to the cursor.

---

## 2:30–2:45 — Hotkey + Reliability

Implement:

```text
Ctrl + Shift + Space
```

Add:

- Error handling.
- Cooldown.
- Duplicate prevention.
- Screen-edge handling.

---

## 2:45–3:00 — Demo Preparation

Prepare:

1. A terminal error.
2. A code editor error.
3. A normal piece of text.
4. A reliable hotkey demonstration.

Practice the pitch.

---

# 17. Demo Scenarios

## Scenario 1 — Python Error

Screen:

```text
ModuleNotFoundError:
No module named 'requests'
```

Expected:

```text
Problem:
The requests package isn't installed.

Fix:
pip install requests
```

---

## Scenario 2 — JavaScript Error

Screen:

```text
TypeError:
Cannot read properties of undefined
```

Expected:

```text
Problem:
Your code is trying to access a property
on an undefined value.

Check where the object is created or returned.
```

---

## Scenario 3 — Normal Text

Screen:

```text
Welcome to the application.
```

Expected:

```text
No technical issue detected.
```

AeroTrace should not hallucinate an error.

---

# 18. Evaluation KPIs

### Context Accuracy

Target:

```text
≥80% successful context extraction
```

### Useful Answers

Target:

```text
≥80% useful responses in demo scenarios
```

### Latency

Target:

```text
<5 seconds from trigger to HUD
```

### Non-Intrusiveness

The user should not need to:

- Switch applications.
- Open a browser.
- Copy/paste text.
- Open a chatbox.

---

# 19. Competitive Differentiation

AeroTrace is not primarily competing on having a smarter chatbot.

Its differentiator is **interaction design**.

Traditional AI:

```text
User
 ↓
Open Chat
 ↓
Copy Context
 ↓
Ask Question
 ↓
Read Answer
 ↓
Return to Work
```

AeroTrace:

```text
User
 ↓
Continue Working
 ↓
Hover
 ↓
AI Understands Context
 ↓
Answer Appears
```

### Core Differentiator

> **AeroTrace puts the agent where the user's attention already is.**

---

# 20. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| OCR is slow | Use a small 400×250 region |
| AI API failure | Keep mock analyzer as fallback |
| Dwell detection unreliable | Provide Ctrl+Shift+Space |
| Voice dependencies fail | Treat voice as optional |
| HUD blocks content | Position beside cursor |
| Screen-edge overflow | Reposition HUD automatically |
| Repeated triggering | Add cooldown/duplicate detection |

---

# 21. Success Criteria

AeroTrace is a successful MVP if a judge can see:

```text
1. User opens an existing application.
             ↓
2. User encounters an error.
             ↓
3. User moves cursor over it.
             ↓
4. AeroTrace detects the context.
             ↓
5. AI understands the content.
             ↓
6. Useful answer appears beside cursor.
             ↓
7. User never opens a chatbox.
```

If this works reliably, the core hackathon objective is achieved.

---

# 22. Future Vision

The MVP focuses on technical errors, but the long-term AeroTrace concept can understand many types of desktop context:

```text
Code errors
     ↓
Design feedback
     ↓
Document assistance
     ↓
Data analysis
     ↓
Email assistance
     ↓
UI explanations
     ↓
Research assistance
     ↓
Cross-application actions
```

Eventually:

> AeroTrace becomes an ambient agent that understands what the user is looking at, what they are trying to accomplish, and what action would help next.

---

# 23. Final MVP Definition

### Input

```text
Cursor location
+
Screen region
+
Optional voice command
```

### Processing

```text
Screen Capture
      ↓
OCR / Vision
      ↓
LangGraph
      ↓
LLM
      ↓
Pydantic Structured Output
```

### Output

```text
Floating contextual HUD
```

### Complete Experience

```text
┌──────────────────────────────────────────────┐
│                 USER DESKTOP                 │
│                                              │
│  Terminal                                    │
│  ┌────────────────────────────────────────┐  │
│  │ ModuleNotFoundError                    │  │
│  │ No module named 'requests'             │  │
│  │                         ↑               │  │
│  │                       CURSOR           │  │
│  └─────────────────────────┼──────────────┘  │
│                            │                 │
│                    ┌───────┴────────┐        │
│                    │ AeroTrace      │        │
│                    │                │        │
│                    │ Missing        │        │
│                    │ requests.      │        │
│                    │                │        │
│                    │ pip install    │        │
│                    │ requests       │        │
│                    └────────────────┘        │
│                                              │
│          NO CHATBOX REQUIRED                 │
└──────────────────────────────────────────────┘
```

---

## Product Principle

> **Don't make the user go to the AI. Bring the AI to the user's context.**
