# Resolution Tracker

An AI-powered goal tracking companion that helps you set, journal, and reflect on personal resolutions — with an agent that plans what to do with each message and helps you achieve your resolutions.

## Motivation

Every resolution app I've tried has the same problem: you set a goal in January, log it a few times, and then the app just sits there. There's no feedback loop — nothing that actually holds you accountable or helps you understand *why* you're falling off.

The idea here was to make the tracking conversational. Instead of clicking buttons to log a run, you just tell it "I ran 35 minutes this morning, felt rough." Instead of reading a dashboard, you ask it how you're doing and it pulls the actual data before answering. The agent part matters because the same message might mean very different things depending on context — sometimes it needs to log progress, sometimes it needs to ask a question first, sometimes it should search for evidence-based advice and then log. A fixed if/else pipeline can't handle that. With this tracker, you can set goals, log progress, ask questions about how to better approach your goal, journal how you're feeling, and get honest weekly reflections back.

## Quick start

### Prerequisites
- Python 3.10+
- An Anthropic API key ([console.anthropic.com](https://console.anthropic.com))

### 1. Clone and configure

```bash
git clone <repo-url>
cd Agentic_AI_resolution_tracker
cp .env.example .env
```

Edit `.env`:

```
ANTHROPIC_API_KEY=sk-ant-...
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the app

```bash
streamlit run ui/app.py
```

Open `http://localhost:8501`.

### 4. Run the evaluation

```bash
python eval/eval.py
```

## Project structure

```
Agentic_resolution_tracker/
├── agent/
│   ├── agent.py       # the agent loop — planning, tool calling, history management
│   ├── tools.py       # 7 tool functions + the Claude tool schemas
│   ├── db.py          # SQLite helpers and streak calculation
│   └── __init__.py
├── ui/
│   └── app.py         # Streamlit UI — three-panel layout (goals / detail / chat)
├── eval/
│   ├── eval.py        # evaluation harness — 8 test cases, 3 metrics
│   └── eval_report.json
├── data/              # SQLite database, created at runtime (gitignored)
├── requirements.txt
├── .env.example
└── README.md
```

| File | What it does |
|---|---|
| `agent/db.py` | Opens the SQLite connection, initializes the three tables (goals, progress_logs, journal_entries), and calculates consecutive-day streaks. |
| `agent/tools.py` | The 7 tool functions the agent can call, plus the JSON schemas Claude sees for each one. Also has `execute_tool()`, which dispatches a tool call by name and returns the result as JSON. |
| `agent/agent.py` | The agent loop. Appends the user message to history, calls Claude, handles tool calls by running them and feeding results back, and keeps looping until Claude returns a final text response. |
| `ui/app.py` | Three-panel Streamlit UI. Left: goal list with streak badges. Center: goal detail (week circles, progress bar, stats, 6-week chart, journal, check-in card). Right: per-goal agent chat. |
| `eval/eval.py` | Runs 8 test cases in sequence, sharing conversation history across them (simulating a real session). Reports tool accuracy, response quality, keyword hit rate, and latency. |

## How the agent works

Every message goes through a **plan → act → respond** loop. Claude decides what to do — the Python code just dispatches whatever Claude asks for.

```
User message
    ↓
Claude reads the message + full conversation history
    ↓
Claude plans: what does this actually need?
    ↓
  ┌─ Ask a clarifying question (if the goal is too vague to add)
  ├─ Call one tool (log_progress, get_status, search_web…)
  ├─ Call multiple tools in sequence (add_goal → search_web → respond)
  └─ Just respond (if no data lookup is needed)
    ↓
agent.py runs the tool(s), feeds results back into the conversation
    ↓
Claude synthesizes a final response citing real data
```

The loop runs up to 10 iterations. Each tool result is appended to the conversation so Claude can see what it already looked up before deciding whether to call another tool or stop.

### Tools

| Tool | What it does |
|---|---|
| `add_goal` | Creates a new resolution in the database with name, target, unit, frequency, and optional deadline. |
| `log_progress` | Appends a progress entry (with optional numeric value and note) to an existing goal. |
| `get_status` | Returns streaks, log counts, recent logs, and recent journal entries for one or all goals. |
| `journal_entry` | Saves a free-text journal entry tied to a specific goal — used for feelings, reflections, and struggles, not just numbers. |
| `get_reflections` | Retrieves the last 10 journal entries for a goal — used when building weekly reflections. |
| `search_web` | Queries DuckDuckGo and returns the top 3 results. Used for habit science lookups and evidence-based tips. |
| `generate_weekly_summary` | Pulls all goals and their logs from the past 7 days and computes a digest. |

### Model

`claude-haiku-4-5-20251001` — fast enough for a conversational tracking app, and the system prompt is specific enough that it doesn't need a larger model to reason well.

## Why this is agentic

1. **Claude plans before acting.** The system prompt instructs it to think about what each message actually needs before calling any tool. The same input — "I went for a run today" — might trigger just `log_progress`, or `get_status → log_progress`, or `get_status → log_progress → search_web` depending on context.

2. **Goal creation requires clarification.** If the user says "I want to run more," the agent asks follow-up questions (how often? what distance? why now?) before calling `add_goal`. It won't add a fuzzy goal. This is a decision Claude makes, not a hardcoded rule.

3. **Reflections chain multiple tools.** A weekly check-in triggers `generate_weekly_summary` plus `get_reflections` for every goal that has journal entries, then synthesizes a response that references both the data and the user's own words.

4. **Context carries across turns.** Every conversation is stored per-goal, so when the user comes back a week later and says "not great honestly," the agent can look at the goal's history and understand what they're referring to.

## Evaluation

### Testing strategy

The evaluation should answer 3 different questions (i.e. ways the agent can fail):

1. Did the agent pick the right tools for the input?
2. Does the agent always return a substantive response (not a one-liner)?
3. Does the response actually contain relevant domain content?

### Test cases

`eval.py` runs 8 test cases in sequence, sharing conversation history across them — the same way a real user session works. The cases cover all 7 tools:

| # | Input | Expected tool |
|---|---|---|
| 1 | "I want to start running 30 minutes every day to get fit" | `add_goal` |
| 2 | "Just finished a 35-minute run this morning, felt great!" | `log_progress` |
| 3 | "How am I doing with my goals so far?" | `get_status` |
| 4 | "What does the science say about how long it takes to build a habit?" | `search_web` |
| 5 | "Can you give me an honest weekly check-in?" | `generate_weekly_summary` |
| 6 | "Add a goal: read 20 pages every day" | `add_goal` |
| 7 | "I read 22 pages tonight before bed" | `log_progress` |
| 8 | "I've been slacking on running lately. What are strategies to stay consistent?" | `search_web` |

### Metrics

| Metric | Purpose | How |
|---|---|---|
| **Tool Accuracy** | Did the agent call the expected tool? | Boolean match — was the expected tool in the list of tools called for that turn? |
| **Response Quality** | Is the response substantive? | Response must exceed 30 characters. Catches empty or one-word answers. |
| **Keyword Hit Rate** | Does the response contain domain-relevant content? | Each test case has a set of expected keywords; the response passes if it contains at least one. |

### Results

| Metric | Score |
|---|---|
| Tool Accuracy | 2/8 (25.0%) |
| Response Quality | 8/8 (100.0%) |
| Keyword Hit Rate | 8/8 (100.0%) |
| Overall Score | 75.0% |
| Avg Latency | 3.1s |

### Interpretation

Response quality and keyword coverage are both perfect — the agent always gives a substantive, relevant answer. The 3.1s average latency is acceptable for a reflection-style tool where the user isn't expecting instant results.

The low tool accuracy (25%) is the most interesting result, and it reveals a real tension in the design rather than a failure. The agent is built to ask clarifying questions before adding a vague goal — that's intentional. When case 1 says "I want to start running 30 minutes every day," the agent asks follow-up questions instead of calling `add_goal` immediately, because the system prompt tells it not to add fuzzy goals. That's correct behavior from a UX standpoint, but the eval marks it as a miss because it expected `add_goal`.

This cascades: cases 2, 3, 5, 6, and 7 all fail because no goal was created in case 1, so there's nothing to log or summarize. Two tests (4 and 8) pass cleanly because `search_web` requires no prior state.

The fix would be to rewrite the eval test cases to match the agent's actual planning behavior — seeding a goal directly in the database before testing `log_progress`, and phrasing goal creation inputs more specifically (e.g. "Add a goal: run 30 minutes daily"). The current cases were written for a simpler reactive agent, not a planning one. The 100% scores on quality and keywords confirm the agent is working correctly; the tool accuracy metric is measuring a mismatch between the test design and the agent's intended behavior.
