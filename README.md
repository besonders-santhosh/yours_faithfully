# 🚀 AeroTrace — Ambient Cursor Co-Pilot

> An ambient desktop AI agent that understands what's underneath your cursor and gives actionable help directly beside it — without opening a chatbox.

---

## 💡 The 3-Input Fusion Concept

AeroTrace operates directly in the desktop workspace where developers already work. Rather than switching to a chatbot, copying error messages, and losing context, AeroTrace fuses three ambient streams into a unified agent state:

1. **👁️ Screen Context (MSS + OCR):** Grabs a 400×250 crop centered on the cursor and extracts the visible error or stack trace.
2. **🎤 Voice Intent (Speech-to-Text):** Quick voice capture for natural questions like *"Why is this crashing?"* or *"How do I start this container?"*.
3. **🔌 MCP Environment Sync:** Connects to developer environment tools to pull active Git branch, Python version, Docker container status, and IDE logs.

---

## 🎮 How to Run

### 1. Launch the AeroTrace Cursor Overlay
```bash
python main.py
```
- **Summon at Cursor:** Press `Ctrl + Shift + Space` anywhere on your desktop.
- **Move Anywhere:** Click and drag the circular orb to place it anywhere on your desktop.
- **Controls on the Circle:**
  - `⚡` Center : Fuse all active inputs and generate solution.
  - `👁️` Top : Crop & read screen text under cursor.
  - `🎤` Right : Record voice intent query.
  - `🔌` Bottom : Sync active workspace/git/container context.
  - `🟢` / `⏸️` Left : Toggle active monitoring status.
  - `✕` Top-Right : Dismiss the overlay.
- **Result Card:** Expands neatly below the circle when resolved, with a one-click `📋 Copy` button.


### 2. Launch the Demo Test Cards (Optional)
To test right away without triggering errors in real code:
```bash
python demo_scenarios.py
```
This opens 4 test cards:
- **Scenario 1:** Python `ModuleNotFoundError: No module named 'requests'`
- **Scenario 2:** JavaScript `TypeError: Cannot read properties of undefined`
- **Scenario 3:** Multi-modal MCP Fusion (`ConnectionRefusedError: port 5432`)
- **Scenario 4:** Normal prose text (verifies zero hallucinations)

---

## 🛠️ Project Structure

```text
yours_faithfully/
├── main.py              # Application entrypoint & global hotkey wiring
├── demo_scenarios.py    # Companion testing cards window
├── config.py            # Global settings & thresholds
├── requirements.txt     # Python dependencies
├── agent/
│   ├── models.py        # Pydantic schemas (AgentState, ErrorAnalysis)
│   └── agent.py         # Multi-modal fusion & reasoning engine
├── capture/
│   ├── mouse.py         # pynput hotkey & dwell monitor
│   ├── screen.py        # mss screen capture around cursor
│   └── ocr.py           # Multi-engine OCR (EasyOCR / WinOCR)
├── context/
│   └── mcp_context.py   # MCP developer environment context provider
├── voice/
│   └── audio.py         # Speech-to-text recording utility
└── ui/
    └── overlay.py       # PyQt5 floating cursor controller & HUD
```

---

## 🔒 Privacy & Performance
- Captures only a 400×250 bounding box around the cursor on demand.
- Does **not** record the screen or store user data continuously.
- Features a built-in instant heuristic reasoning engine ensuring zero-latency offline demo reliability, with optional cloud LLM (Groq / OpenAI) support via `.env`.
