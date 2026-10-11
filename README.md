# Home Credit LAP Voice Agent

A local browser based simulator for the Home Credit Loan Against Property (LAP) qualification flow. The app conducts a simulated conversation, tracks the seven qualification items, and displays the current decision and transcript. Its qualification engine is rule based; you do not need an LLM key, voice platform account, or cloud service to run it locally.

`spec.md` is the source of truth for eligibility and conversation behavior. The project must not infer additional product terms such as a minimum property value, fees, rates, or processing timelines. Exact interest rates are left to the senior loan expert.

## Requirements

- Python 3.10 or later
- A modern browser such as Chrome or Edge (recommended for browser speech recognition)
- Microphone permission for voice input; typing replies works without a microphone

No Node.js installation is needed. Python serves both the API and frontend.

## Run locally

Open a terminal in the project root (the directory containing `spec.md` and `start.bat`), then create and activate a virtual environment.

### Windows PowerShell

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r backend\requirements.txt
python backend\run_server.py
```

If PowerShell blocks virtual environment activation, use Command Prompt instead:

```bat
py -3 -m venv .venv
.venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r backend\requirements.txt
python backend\run_server.py
```

### macOS or Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt
python backend/run_server.py
```

When the server starts, it opens the app in your browser. If it does not, visit **http://127.0.0.1:8000**. Keep the terminal open while using the app. Press **Ctrl+C** in that terminal to stop the server.

The convenience launchers `start.bat` (Windows) and `start.sh` (macOS/Linux) are also available. They install dependencies into the currently active Python environment and start the server; activate `.venv` first so packages stay project-local.

## Use the simulator

1. Enter the customer name in the opening dialog.
2. Select **Start Call** to hear the agent greeting.
3. Reply by typing in the response box and submitting, or use the microphone button if your browser supports speech recognition and microphone access is allowed.
4. Watch the transcript and qualification matrix update. The suggestions are shortcuts for sample customer replies.
5. Use **Reset** to start a fresh session. The tabs show the qualification matrix, scenario suite, prompt configuration, and telemetry.

The interface uses browser speech synthesis for agent audio and browser speech recognition for optional customer input. Recognition support depends on browser and system settings; typing remains available.

## Conversation rules implemented

- Verify the intended customer, handle busy customers by requesting a callback time, present the offer up to ₹75,00,000, and detect existing property loans or EMI reduction requests.
- Collect property type, ownership, original document availability, loan amount, occupation and income mode, estimated market value, and repayment tenure. Capture clear out-of-order answers and ask for the earliest unanswered item.
- Agricultural property, unavailable original documents, cash income, and tenure outside 3–15 years disqualify the caller.
- For a request above ₹75,00,000, explain the cap and ask whether the customer wants to continue at the maximum amount.
- Only hand off to a senior loan expert after all seven checklist items are answered and pass the applicable criteria. Market value is recorded without adding an unstated minimum.

## Project files

```text
backend/                 FastAPI API and qualification state machine
frontend/                Browser UI, styles, and interaction logic
prompts/                 English/Hindi system prompts and voice platform config examples
spec.md                  Single source of truth for requirements
start.bat                Windows convenience launcher
start.sh                 macOS/Linux convenience launcher
```

## Local API

The API documentation is available at **http://127.0.0.1:8000/docs** while the server is running.

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/health` | Check that the backend is running |
| `POST` | `/api/session/start` | Reset and begin a call with the greeting |
| `POST` | `/api/chat` | Submit a customer utterance |
| `POST` | `/api/session/reset` | Reset the current session |
| `GET` | `/api/state` | Read qualification state and rendered prompt |
| `POST` | `/api/config` | Update prompt variables and product context |
| `GET` | `/api/prompt` | Read raw and rendered system prompt |
| `GET` | `/api/test-scenarios/run-all` | Run and return the evaluation scenarios |

For a different port, set `PORT` before starting. In PowerShell use `$env:PORT = "8001"`; in macOS/Linux use `PORT=8001 python backend/run_server.py`. Then open the corresponding `http://127.0.0.1:<port>` address.

## Scope

This is a local simulation. It does not place real phone calls, connect to Retell or Bolna, or create hosted recordings or public call-log links. The example platform configurations and prompts in `prompts/` are provided for a separate hosted deployment workflow.
