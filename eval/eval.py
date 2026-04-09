import sys
import os
import time
import json
from pathlib import Path

# add the project root to the path so we can import from agent/
sys.path.insert(0, str(Path(__file__).parent.parent))

# redirect the db to a throwaway test file so we don't mess with real data
import agent.db as _db
_db.DB_PATH = Path(__file__).parent.parent / "data" / "test_resolutions.db"

from agent.agent import run_agent_debug
from agent.db import init_db

# each test case has an expected tool — we check if the agent actually called it
# the cases run in order and share conversation history, just like a real user session
TEST_CASES = [
    {
        "id": 1,
        "description": "Create a fitness goal",
        "input": "I want to start running 30 minutes every day to get fit",
        "expected_tool": "add_goal",
        "keywords": ["goal", "running", "added", "created", "track"],
    },
    {
        "id": 2,
        "description": "Log progress on existing goal",
        "input": "Just finished a 35-minute run this morning, felt great!",
        "expected_tool": "log_progress",
        "keywords": ["logged", "progress", "run", "streak", "keep"],
    },
    {
        "id": 3,
        "description": "Check goal status",
        "input": "How am I doing with my goals so far?",
        "expected_tool": "get_status",
        "keywords": ["streak", "log", "goal", "day"],
    },
    {
        "id": 4,
        "description": "Search for habit-building tips",
        "input": "What does the science say about how long it takes to build a habit?",
        "expected_tool": "search_web",
        "keywords": ["day", "habit", "research", "study", "week"],
    },
    {
        "id": 5,
        "description": "Request weekly summary",
        "input": "Can you give me an honest weekly check-in?",
        "expected_tool": "generate_weekly_summary",
        "keywords": ["week", "goal", "log", "streak"],
    },
    {
        "id": 6,
        "description": "Create a reading goal",
        "input": "Add a goal: read 20 pages every day",
        "expected_tool": "add_goal",
        "keywords": ["goal", "read", "page", "added", "created", "track"],
    },
    {
        "id": 7,
        "description": "Log reading progress",
        "input": "I read 22 pages tonight before bed",
        "expected_tool": "log_progress",
        "keywords": ["logged", "read", "page", "progress", "streak"],
    },
    {
        "id": 8,
        "description": "Ask for motivation strategies",
        "input": "I've been slacking on running lately. What are strategies to stay consistent?",
        "expected_tool": "search_web",
        "keywords": ["consistent", "habit", "tip", "strategy", "try", "research"],
    },
]

# anything shorter than this is basically an empty response — counts as a failure
MIN_RESPONSE_LENGTH = 30


# runs all test cases sequentially, prints results, and saves a json report
def run_eval():
    # always start fresh so previous test runs don't affect results
    if _db.DB_PATH.exists():
        _db.DB_PATH.unlink()
    init_db()

    print("=" * 60)
    print("  Resolution Tracker Agent — Evaluation")
    print("=" * 60)
    print(f"  Test cases : {len(TEST_CASES)}")
    print(f"  Model      : claude-haiku-4-5-20251001")
    print(f"  Database   : {_db.DB_PATH.name} (fresh)")
    print("=" * 60)
    print()

    # shared history across test cases — simulates a real conversation
    history: list = []
    results = []

    for tc in TEST_CASES:
        print(f"[{tc['id']}/{len(TEST_CASES)}] {tc['description']}")
        print(f"  Input : \"{tc['input']}\"")

        t0 = time.time()
        response, history, tools_called = run_agent_debug(tc["input"], history)
        latency = time.time() - t0

        # three checks: did it use the right tool, is the response long enough, does it mention the right words
        tool_ok = tc["expected_tool"] in tools_called
        quality_ok = len(response.strip()) >= MIN_RESPONSE_LENGTH
        kw_hit = any(kw.lower() in response.lower() for kw in tc["keywords"])

        print(f"  Tools called    : {tools_called}")
        print(f"  Expected tool   : {tc['expected_tool']}  {'✓' if tool_ok else '✗'}")
        print(f"  Response length : {len(response)} chars  {'✓' if quality_ok else '✗'}")
        print(f"  Keyword hit     : {kw_hit}  {'✓' if kw_hit else '✗'}")
        print(f"  Latency         : {latency:.1f}s")
        print(f"  {'PASS' if (tool_ok and quality_ok) else 'FAIL'}")
        print()

        results.append(
            {
                "id": tc["id"],
                "description": tc["description"],
                "tool_ok": tool_ok,
                "quality_ok": quality_ok,
                "kw_hit": kw_hit,
                "latency": latency,
                "response_len": len(response),
                "tools_called": tools_called,
                "expected_tool": tc["expected_tool"],
            }
        )

    # calculate aggregate scores across all test cases
    n = len(results)
    tool_acc = sum(r["tool_ok"]    for r in results) / n * 100
    quality  = sum(r["quality_ok"] for r in results) / n * 100
    kw_rate  = sum(r["kw_hit"]     for r in results) / n * 100
    overall  = (tool_acc + quality + kw_rate) / 3
    avg_lat  = sum(r["latency"]    for r in results) / n

    print("=" * 60)
    print("  RESULTS")
    print("=" * 60)
    print(f"  Tool Accuracy    : {sum(r['tool_ok'] for r in results)}/{n}  ({tool_acc:.1f}%)")
    print(f"  Response Quality : {sum(r['quality_ok'] for r in results)}/{n}  ({quality:.1f}%)")
    print(f"  Keyword Hit Rate : {sum(r['kw_hit'] for r in results)}/{n}  ({kw_rate:.1f}%)")
    print(f"  Overall Score    : {overall:.1f}%")
    print(f"  Avg Latency      : {avg_lat:.1f}s")
    print("=" * 60)

    # save detailed results to json so you can look at individual cases later
    report_path = Path(__file__).parent / "eval_report.json"
    report = {
        "tool_accuracy_pct": round(tool_acc, 2),
        "response_quality_pct": round(quality, 2),
        "keyword_hit_rate_pct": round(kw_rate, 2),
        "overall_score_pct": round(overall, 2),
        "avg_latency_s": round(avg_lat, 2),
        "cases": results,
    }
    report_path.write_text(json.dumps(report, indent=2))
    print(f"\n  Full report saved to: {report_path}")

    return report


if __name__ == "__main__":
    run_eval()
