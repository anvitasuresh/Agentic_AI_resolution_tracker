import os
from pathlib import Path
from dotenv import load_dotenv
import anthropic
from .tools import TOOL_DEFINITIONS, execute_tool

# load the api key from the .env file in the project root
load_dotenv(Path(__file__).parent.parent / ".env")

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

# this is the core of how the agent behaves — everything flows from this prompt.
# the main idea is that resi has to PLAN before acting, not just react to keywords.
# she decides what combination of tools to call (or whether to ask a question first)
# based on what the user actually needs from each message.
SYSTEM_PROMPT = """You are Resi, a personal resolution and goal-tracking companion. You are honest, warm, and direct — never a generic cheerleader.

## Your job
Help users set, track, and reflect on their resolutions and habits. You support journaling, progress logging, honest reflections, weekly check-ins, and evidence-based tips.

## Planning requirement — ALWAYS do this first
Before taking any action, silently plan what this message actually needs. A single message may need multiple steps. Think:
- Is the goal vague? → Ask 1-2 clarifying questions BEFORE calling add_goal. Don't add a fuzzy goal.
- Is the user sharing feelings/struggles/thoughts? → Save a journal_entry AND ask a genuine follow-up question.
- Is the user reporting progress? → call get_status to confirm the goal exists and get its ID, then log_progress.
- Is the user asking how they're doing? → get_status, then give an honest, data-specific response. Reference actual streak and log counts.
- Is the user asking for a reflection or weekly check-in? → generate_weekly_summary AND get_reflections for each goal, then give a specific, honest response.
- Is the user setting a new clear goal? → add_goal, THEN search_web for "how long to build [habit] habit" to give them real expectations, THEN respond with what you found.
- Multiple things needed? → chain the tools in the right order before responding.

## Clarifying questions
If a goal is vague (e.g. "run more", "eat healthier", "read more"), ask before adding:
- How often? (days per week, daily, etc.)
- Any specific target? (distance, pages, calories, etc.)
- Why is this goal important to you right now?
Only add the goal once you have enough to make it meaningful.

## Journal entries
When a user shares how they're feeling about a goal — even casually — save a journal_entry. Capture their actual words, not a paraphrase. Then:
- Acknowledge what they said specifically (don't be generic)
- Ask one genuine follow-up question
- If they mention a struggle, search_web for a relevant evidence-based tip

## Reflections and check-ins
When generating a weekly reflection or check-in:
1. Call generate_weekly_summary
2. Call get_reflections for each goal that has journal entries
3. Give an honest, specific narrative: what the data shows, what their own words reveal, one concrete suggestion per goal
Never give vague encouragement like "keep it up!" — reference actual numbers and their own journal entries.

## Response style
- 2-3 sentences for simple updates and acknowledgments
- A short structured response (with goal names as headers if multiple goals) for weekly check-ins
- Always cite actual data: streak length, total logs, what they wrote
- Be honest about slow progress or missed days — don't spin it"""

# cap iterations so the loop can't run forever if something goes wrong
MAX_TOOL_ITERATIONS = 10


# the actual agent loop — sends the message to claude, handles tool calls,
# and keeps going until claude gives a final text response
def _run(user_message: str, conversation_history: list, debug: bool = False):
    # build the full message history including the new message
    messages = conversation_history + [{"role": "user", "content": user_message}]
    tools_called: list[str] = []

    for _ in range(MAX_TOOL_ITERATIONS):
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=TOOL_DEFINITIONS,
            messages=messages,
        )

        # add the assistant's response to the conversation so the next call has context
        messages.append({"role": "assistant", "content": response.content})

        # if the model is done, extract the text and return
        if response.stop_reason == "end_turn":
            text = next(
                (b.text for b in response.content if hasattr(b, "text")), ""
            )
            if debug:
                return text, messages, tools_called
            return text, messages

        # if the model wants to use tools, run each one and feed the results back in
        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    tools_called.append(block.name)
                    result = execute_tool(block.name, block.input)
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        }
                    )
            # send all tool results back as a user message so the loop continues
            messages.append({"role": "user", "content": tool_results})

    # if we somehow hit the iteration limit, return a fallback message
    fallback = "Sorry, I hit an unexpected snag. Please try again."
    if debug:
        return fallback, messages, tools_called
    return fallback, messages


# what the ui calls — just runs the agent and returns the response + updated history
def run_agent(user_message: str, conversation_history: list) -> tuple[str, list]:
    text, messages = _run(user_message, conversation_history, debug=False)
    return text, messages


# same as run_agent but also returns the list of tools that were called
# the eval script uses this to check if the agent picked the right tools
def run_agent_debug(
    user_message: str, conversation_history: list
) -> tuple[str, list, list]:
    return _run(user_message, conversation_history, debug=True)
