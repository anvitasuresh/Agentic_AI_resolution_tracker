import json
from datetime import datetime, timedelta
from .db import get_connection, init_db, calculate_streak


# inserts a new goal row into the database
# the agent calls this after asking clarifying questions and getting enough info
def add_goal(name: str, target: float = None, unit: str = None,
             frequency: str = "daily", deadline: str = None) -> dict:
    init_db()
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO goals (name, target, unit, frequency, deadline) VALUES (?, ?, ?, ?, ?)",
        (name, target, unit, frequency, deadline),
    )
    goal_id = cur.lastrowid
    conn.commit()
    conn.close()
    return {"success": True, "goal_id": goal_id, "message": f"Goal '{name}' created (ID {goal_id})."}


# logs a single progress entry for a goal
# value is optional — sometimes the user just wants to say "did it" without a number
def log_progress(goal_id: int, value: float = None, note: str = None) -> dict:
    init_db()
    conn = get_connection()
    # make sure the goal actually exists before trying to log
    goal = conn.execute("SELECT * FROM goals WHERE id = ?", (goal_id,)).fetchone()
    if not goal:
        conn.close()
        return {"success": False, "error": f"No goal with ID {goal_id}."}
    conn.execute(
        "INSERT INTO progress_logs (goal_id, value, note) VALUES (?, ?, ?)",
        (goal_id, value, note),
    )
    conn.commit()
    conn.close()
    return {"success": True, "message": f"Progress logged for '{goal['name']}'."}


# returns streak + recent logs for one goal or all of them
# the agent uses this before giving any feedback so it's working with real data
def get_status(goal_id: int = None) -> dict:
    init_db()
    conn = get_connection()
    if goal_id:
        goals = conn.execute("SELECT * FROM goals WHERE id = ?", (goal_id,)).fetchall()
    else:
        goals = conn.execute("SELECT * FROM goals ORDER BY created_at").fetchall()

    results = []
    for g in goals:
        # grab up to 60 logs — enough to calculate a meaningful streak
        logs = conn.execute(
            "SELECT * FROM progress_logs WHERE goal_id = ? ORDER BY logged_at DESC LIMIT 60",
            (g["id"],),
        ).fetchall()
        streak = calculate_streak(logs)

        # also pull the most recent journal entries so the agent has context
        recent_journals = conn.execute(
            "SELECT text, written_at FROM journal_entries WHERE goal_id = ? ORDER BY written_at DESC LIMIT 3",
            (g["id"],),
        ).fetchall()
        results.append({
            "id": g["id"],
            "name": g["name"],
            "target": g["target"],
            "unit": g["unit"],
            "frequency": g["frequency"],
            "deadline": g["deadline"],
            "current_streak": streak,
            "total_logs": len(logs),
            # only send the 5 most recent logs to keep the response small
            "recent_logs": [
                {"date": l["logged_at"], "value": l["value"], "note": l["note"]}
                for l in logs[:5]
            ],
            "recent_journal": [
                {"text": j["text"], "date": j["written_at"]} for j in recent_journals
            ],
        })
    conn.close()
    return {"goals": results, "total_goals": len(results)}


# saves a free-text journal entry for a goal
# used when the user shares feelings or reflections, not just numbers
def journal_entry(goal_id: int, text: str) -> dict:
    init_db()
    conn = get_connection()
    goal = conn.execute("SELECT * FROM goals WHERE id = ?", (goal_id,)).fetchone()
    if not goal:
        conn.close()
        return {"success": False, "error": f"No goal with ID {goal_id}."}
    conn.execute(
        "INSERT INTO journal_entries (goal_id, text) VALUES (?, ?)",
        (goal_id, text),
    )
    conn.commit()
    conn.close()
    return {"success": True, "message": f"Journal entry saved for '{goal['name']}'."}


# pulls back the last 10 journal entries for a goal
# the agent uses this when building a weekly reflection so it can reference real words
def get_reflections(goal_id: int) -> dict:
    init_db()
    conn = get_connection()
    goal = conn.execute("SELECT * FROM goals WHERE id = ?", (goal_id,)).fetchone()
    if not goal:
        conn.close()
        return {"error": f"No goal with ID {goal_id}."}
    entries = conn.execute(
        "SELECT text, written_at FROM journal_entries WHERE goal_id = ? ORDER BY written_at DESC LIMIT 10",
        (goal_id,),
    ).fetchall()
    conn.close()
    return {
        "goal": goal["name"],
        "journal_entries": [{"text": e["text"], "date": e["written_at"]} for e in entries],
    }


# searches duckduckgo and returns the top 3 results
# used for habit science lookups and motivation tips
def search_web(query: str) -> dict:
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            hits = list(ddgs.text(query, max_results=3))
        return {
            "query": query,
            "results": [
                {"title": h["title"], "snippet": h["body"], "url": h["href"]}
                for h in hits
            ],
        }
    except Exception as exc:
        # if the search fails for any reason, return an empty result rather than crashing
        return {"query": query, "error": str(exc), "results": []}


# builds a summary of every goal for the past 7 days
# called by the agent for weekly check-ins
def generate_weekly_summary() -> dict:
    init_db()
    conn = get_connection()
    goals = conn.execute("SELECT * FROM goals ORDER BY created_at").fetchall()
    week_ago = (datetime.now() - timedelta(days=7)).isoformat()

    summary = []
    for g in goals:
        # get only the logs from this past week
        week_logs = conn.execute(
            "SELECT * FROM progress_logs WHERE goal_id = ? AND logged_at > ? ORDER BY logged_at",
            (g["id"], week_ago),
        ).fetchall()
        # need all logs (not just this week) to calculate the current streak accurately
        all_logs = conn.execute(
            "SELECT * FROM progress_logs WHERE goal_id = ? ORDER BY logged_at DESC LIMIT 60",
            (g["id"],),
        ).fetchall()
        streak = calculate_streak(all_logs)
        summary.append({
            "goal": g["name"],
            "frequency": g["frequency"],
            "logs_this_week": len(week_logs),
            "current_streak": streak,
            "notes_this_week": [l["note"] for l in week_logs if l["note"]],
        })
    conn.close()
    return {"week_ending": datetime.now().strftime("%Y-%m-%d"), "goals": summary}


# these are the tool definitions claude needs to know what tools exist and how to call them
# every tool above has a matching entry here with its input schema
TOOL_DEFINITIONS = [
    {
        "name": "add_goal",
        "description": (
            "Create a new resolution or goal for the user to track. "
            "Call this when the user expresses wanting to start or track a new goal."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name":      {"type": "string",  "description": "Short descriptive name of the goal"},
                "target":    {"type": "number",  "description": "Numeric target (e.g. 30 for '30 minutes')"},
                "unit":      {"type": "string",  "description": "Unit of measurement (minutes, pages, miles…)"},
                "frequency": {"type": "string",  "enum": ["daily", "weekly"], "description": "How often the goal should be completed"},
                "deadline":  {"type": "string",  "description": "Optional deadline in YYYY-MM-DD format"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "log_progress",
        "description": (
            "Log a progress entry for an existing goal. "
            "Call this whenever the user reports completing or making progress on something. "
            "If you don't know the goal_id, call get_status first."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "goal_id": {"type": "integer", "description": "ID of the goal"},
                "value":   {"type": "number",  "description": "Numeric amount completed (optional)"},
                "note":    {"type": "string",  "description": "Short note about the session"},
            },
            "required": ["goal_id"],
        },
    },
    {
        "name": "get_status",
        "description": (
            "Fetch the current status of goals including streaks and recent logs. "
            "Call this before giving progress feedback or when the user asks how they're doing."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "goal_id": {"type": "integer", "description": "Specific goal ID (omit for all goals)"},
            },
        },
    },
    {
        "name": "search_web",
        "description": (
            "Search the web for motivation tips, habit science, or strategies related to a goal. "
            "Use this when the user asks for advice, tips, or 'what does the research say'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "generate_weekly_summary",
        "description": (
            "Generate a full weekly digest across all goals. "
            "Use this for weekly check-ins or when the user asks for a summary/report."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "journal_entry",
        "description": (
            "Save a journal entry capturing the user's thoughts, feelings, struggles, or reflections "
            "about a specific goal. Use this when the user is sharing how they feel, what's been hard, "
            "what's going well, or writing about their experience — not just reporting a numeric result."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "goal_id": {"type": "integer", "description": "ID of the goal this journal entry relates to"},
                "text":    {"type": "string",  "description": "The journal entry text to save"},
            },
            "required": ["goal_id", "text"],
        },
    },
    {
        "name": "get_reflections",
        "description": (
            "Retrieve past journal entries for a goal to inform a reflection or weekly check-in. "
            "Use this when generating reflections or when the user asks you to look back at their journey."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "goal_id": {"type": "integer", "description": "ID of the goal to retrieve journal entries for"},
            },
            "required": ["goal_id"],
        },
    },
]

# maps tool names (strings) to their actual python functions
# execute_tool uses this to look up which function to call
_FUNCTIONS = {
    "add_goal": add_goal,
    "log_progress": log_progress,
    "get_status": get_status,
    "search_web": search_web,
    "generate_weekly_summary": generate_weekly_summary,
    "journal_entry": journal_entry,
    "get_reflections": get_reflections,
}


# called by the agent loop whenever claude decides to use a tool
# looks up the function, runs it, and returns the result as a json string
def execute_tool(name: str, inputs: dict) -> str:
    fn = _FUNCTIONS.get(name)
    if fn is None:
        return json.dumps({"error": f"Unknown tool: {name}"})
    try:
        return json.dumps(fn(**inputs))
    except Exception as exc:
        return json.dumps({"error": str(exc)})
