"""
Streamlit UI for the Resolution Tracker agent.
Run: streamlit run ui/app.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import plotly.graph_objects as go
from datetime import datetime, timedelta

from agent.agent import run_agent
from agent.db import init_db, get_connection, calculate_streak

st.set_page_config(page_title="Resolution Tracker", layout="wide",
                   initial_sidebar_state="collapsed")
init_db()

# sunset palette — mauve, terracotta, orange, yellow, cream, sky blue
PRIMARY = "#C87858"   # warm terracotta (main accent)
DARK    = "#4A2838"   # deep warm dark for text
MUTED   = "#A07880"   # warm muted rose for secondary text
BORDER  = "#E8C8A8"   # soft peach border
ACTIVE  = "rgba(220,160,120,0.35)"  # warm peach for active goal
STAT1   = "#C87858"   # terracotta
STAT2   = "#7BBCD0"   # sky blue
STAT3   = "#A0627A"   # mauve
DOTS    = ["#E8906A","#E07888","#A87098","#7BBCD0","#E8C058","#C8A880"]

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,400;0,500;0,600;1,400&display=swap');

/* universal lora font */
*, *::before, *::after,
html, body, [class*="css"], .stApp,
h1,h2,h3,h4,h5,h6,p,span,div,a,li,label,input,textarea,button,select,
.stButton>button, .stTextInput input, .stMarkdown, .stMarkdown p,
[data-testid="stChatInput"] textarea, [data-testid="stChatInput"] input,
[data-baseweb="input"] input, [data-baseweb="textarea"] textarea {
    font-family: 'Lora', Georgia, serif !important;
    -webkit-font-smoothing: antialiased;
}

/* sunset ombre background — top sky blue fading down through yellow, orange, rose, to mauve */
.stApp, [data-testid="stAppViewContainer"] {
    background: linear-gradient(
        to bottom,
        #C8E8F4 0%,
        #F0E8B0 18%,
        #F5C888 35%,
        #EDA898 52%,
        #D88AAC 72%,
        #B87898 100%
    ) !important;
    min-height: 100vh;
}

#MainMenu, footer, header { display: none !important; }
.main .block-container { padding: 0 !important; max-width: 100% !important; }

/* sidebar — warm mauve/rose tint, semi-transparent so gradient shows through */
div[data-testid="stHorizontalBlock"] > div:nth-child(1) > div[data-testid="stVerticalBlock"],
div[data-testid="stHorizontalBlock"] > div:nth-child(1) > div[data-testid="stVerticalBlockBorderWrapper"] {
    background: rgba(210, 155, 140, 0.38) !important;
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    min-height: 100vh;
    padding: 2rem 1.6rem !important;
    border-right: 1px solid rgba(220, 160, 130, 0.35);
}

/* middle panel — warm cream, mostly opaque so content is readable */
div[data-testid="stHorizontalBlock"] > div:nth-child(2) > div[data-testid="stVerticalBlock"],
div[data-testid="stHorizontalBlock"] > div:nth-child(2) > div[data-testid="stVerticalBlockBorderWrapper"] {
    background: rgba(255, 248, 235, 0.82) !important;
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    padding: 2rem 2.5rem !important;
    min-height: 100vh;
}

/* chat panel — soft sky blue tint, semi-transparent */
div[data-testid="stHorizontalBlock"] > div:nth-child(3) > div[data-testid="stVerticalBlock"],
div[data-testid="stHorizontalBlock"] > div:nth-child(3) > div[data-testid="stVerticalBlockBorderWrapper"] {
    background: rgba(170, 215, 235, 0.38) !important;
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    min-height: 100vh;
    padding: 2rem 1.6rem !important;
    border-left: 1px solid rgba(160, 200, 220, 0.35);
}

/* all buttons base */
.stButton > button {
    font-family: 'Lora', Georgia, serif !important;
    font-size: 0.9rem !important;
    border-radius: 12px !important;
    cursor: pointer !important;
    transition: all 0.15s ease !important;
    letter-spacing: 0.01em !important;
}

/* primary — warm terracotta filled */
.btn-primary .stButton > button {
    background: #C87858 !important;
    color: white !important;
    border: none !important;
    width: 100% !important;
    padding: 13px 20px !important;
    border-radius: 14px !important;
    font-size: 0.95rem !important;
}
.btn-primary .stButton > button:hover {
    background: #B86848 !important;
    box-shadow: 0 4px 14px rgba(200,120,88,0.4) !important;
}

/* ghost — white outlined */
.btn-ghost .stButton > button {
    background: rgba(255,248,235,0.7) !important;
    color: #C87858 !important;
    border: 1.5px solid #E8C8A8 !important;
    padding: 10px 18px !important;
}
.btn-ghost .stButton > button:hover { background: rgba(255,240,220,0.9) !important; }

/* soft action (start reflection) */
.btn-soft .stButton > button {
    background: rgba(255,240,220,0.8) !important;
    color: #C87858 !important;
    border: 1.5px solid #E8C8A8 !important;
    width: 100% !important;
    padding: 12px !important;
}
.btn-soft .stButton > button:hover { background: rgba(255,228,200,0.95) !important; }

/* goal list buttons (inactive) */
.btn-goal .stButton > button {
    background: transparent !important;
    border: none !important;
    width: 100% !important;
    text-align: left !important;
    padding: 10px 14px !important;
    color: #4A2838 !important;
    border-radius: 10px !important;
    margin-bottom: 2px !important;
    justify-content: flex-start !important;
}
.btn-goal .stButton > button:hover { background: rgba(220,160,120,0.3) !important; }

/* text input */
.stTextInput > div > div > input {
    font-family: 'Lora', Georgia, serif !important;
    border-radius: 12px !important;
    border: 1.5px solid #E8C8A8 !important;
    background: rgba(255,248,235,0.9) !important;
    padding: 10px 14px !important;
    color: #4A2838 !important;
    font-size: 0.9rem !important;
}
.stTextInput > div > div > input:focus {
    border-color: #C87858 !important;
    box-shadow: 0 0 0 3px rgba(200,120,88,0.18) !important;
    outline: none !important;
}
.stTextInput > label { font-family: 'Lora', serif !important; }

/* chat input */
[data-testid="stChatInput"] { border-radius: 14px !important; }
[data-testid="stChatInput"] textarea,
[data-testid="stChatInput"] input {
    font-family: 'Lora', Georgia, serif !important;
    font-size: 0.875rem !important;
    border: 1.5px solid rgba(200,160,140,0.5) !important;
    border-radius: 14px !important;
    background: rgba(255,248,235,0.85) !important;
}

/* scrollbar */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(200,140,100,0.4); border-radius: 4px; }
</style>
""", unsafe_allow_html=True)

# ── Helpers ───────────────────────────────────────────────────────────────────
def load_goals():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM goals ORDER BY created_at").fetchall()
    out = []
    for g in rows:
        logs = conn.execute(
            "SELECT * FROM progress_logs WHERE goal_id=? ORDER BY logged_at DESC", (g["id"],)
        ).fetchall()
        journals = conn.execute(
            "SELECT text, written_at FROM journal_entries WHERE goal_id=? ORDER BY written_at DESC LIMIT 6",
            (g["id"],),
        ).fetchall()
        logged_dates: set = set()
        for log in logs:
            try: logged_dates.add(datetime.fromisoformat(str(log["logged_at"])).date())
            except Exception: pass
        streak = calculate_streak(logs)
        best   = _best_streak(logged_dates)
        created = _pd(g["created_at"])
        days_active = max(1, (datetime.now().date() - created).days + 1)
        consistency = min(100, round(len(logged_dates) / days_active * 100))
        out.append({
            "id": g["id"], "name": g["name"], "unit": g["unit"],
            "frequency": g["frequency"], "target": g["target"],
            "created_at": g["created_at"],
            "streak": streak, "best_streak": best,
            "total_logs": sum(l["value"] for l in logs if l["value"] is not None),
            "logs": logs, "logged_dates": logged_dates,
            "journals": [{"text": j["text"], "date": j["written_at"]} for j in journals],
        })
    conn.close()
    return out

def _pd(val):
    try: return datetime.fromisoformat(str(val)).date()
    except Exception: return datetime.now().date()

def _best_streak(ld: set) -> int:
    if not ld: return 0
    sd = sorted(ld); best = cur = 1
    for i in range(1, len(sd)):
        cur = cur + 1 if (sd[i] - sd[i-1]).days == 1 else 1
        best = max(best, cur)
    return best

def week_status(logged_dates: set):
    today = datetime.now().date()
    mon   = today - timedelta(days=today.weekday())
    return [{"letter": "MTWTTFS"[i], "logged": (mon+timedelta(i)) in logged_dates,
             "today": (mon+timedelta(i)) == today, "future": (mon+timedelta(i)) > today}
            for i in range(7)]

def six_week_data(logs):
    today = datetime.now().date()
    mon   = today - timedelta(days=today.weekday())
    out   = []
    for i in range(5, -1, -1):
        ws = mon - timedelta(weeks=i); we = ws + timedelta(days=6)
        ct = sum(1 for l in logs if ws <= _pd(l["logged_at"]) <= we)
        out.append(("Now" if i == 0 else f"–{i}w", ct))
    return out

def week_count(logs):
    today = datetime.now().date(); mon = today - timedelta(days=today.weekday())
    return sum(1 for l in logs if _pd(l["logged_at"]) >= mon)

def circle_svg(color: str, size=44) -> str:
    """Concentric circles icon (no emoji)."""
    c = size // 2
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}">'
            f'<circle cx="{c}" cy="{c}" r="{c-2}" fill="none" stroke="{color}" stroke-width="2.5"/>'
            f'<circle cx="{c}" cy="{c}" r="{c-9}" fill="none" stroke="{color}" stroke-width="2.5"/>'
            f'<circle cx="{c}" cy="{c}" r="{c-16}" fill="{color}"/></svg>')

# ── Session state ──────────────────────────────────────────────────────────────
for k, v in [("selected_id", None), ("show_add", False), ("goal_chats", {})]:
    if k not in st.session_state: st.session_state[k] = v

# global chat key (for adding goals before any exist)
GLOBAL = "__global__"
if GLOBAL not in st.session_state.goal_chats:
    st.session_state.goal_chats[GLOBAL] = {"messages": [], "history": []}

goals = load_goals()
if goals and st.session_state.selected_id is None:
    st.session_state.selected_id = goals[0]["id"]
if not goals:
    st.session_state.selected_id = None

sg = next((g for g in goals if g["id"] == st.session_state.selected_id), None)

# current chat (per-goal or global)
chat_key = st.session_state.selected_id if st.session_state.selected_id else GLOBAL
if chat_key not in st.session_state.goal_chats:
    st.session_state.goal_chats[chat_key] = {"messages": [], "history": []}
chat = st.session_state.goal_chats[chat_key]

# ── Layout ────────────────────────────────────────────────────────────────────
left, mid, right = st.columns([1.4, 2.8, 2.0], gap="small")


# ════════════════════════════════════════
# LEFT — sidebar
# ════════════════════════════════════════
with left:
    st.markdown(f"""
    <div style="margin-bottom:24px;">
      <div style="font-size:1.45rem;font-weight:600;color:{DARK};letter-spacing:-0.02em;
                  font-family:'Lora',serif;">Resolution Tracker</div>
      <div style="font-size:0.8rem;color:{MUTED};font-style:italic;margin-top:4px;
                  font-family:'Lora',serif;">track your goals with AI coaching</div>
    </div>
    <hr style="border:none;border-top:1px solid {BORDER};margin:0 0 20px;">
    """, unsafe_allow_html=True)

    # Add button
    st.markdown('<div class="btn-primary">', unsafe_allow_html=True)
    if st.button("+ New Resolution", use_container_width=True, key="add_btn"):
        st.session_state.show_add = not st.session_state.show_add
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    if st.session_state.show_add:
        st.markdown("<div style='margin-top:10px;'>", unsafe_allow_html=True)
        new_text = st.text_input("", placeholder="What's your resolution?",
                                 label_visibility="collapsed", key="new_res_input")
        st.markdown('<div class="btn-ghost" style="margin-top:6px;">', unsafe_allow_html=True)
        if st.button("Submit →", key="submit_new"):
            if new_text.strip():
                st.session_state.show_add = False
                prompt = new_text.strip()
                gc = st.session_state.goal_chats[GLOBAL]
                gc["messages"].append({"role": "user", "content": prompt})
                with st.spinner("Thinking…"):
                    resp, new_hist = run_agent(prompt, gc["history"])
                gc["history"] = new_hist
                gc["messages"].append({"role": "assistant", "content": resp})
                st.session_state.selected_id = None  # show global chat
                st.rerun()
        st.markdown('</div></div>', unsafe_allow_html=True)

    if goals:
        st.markdown(f"""
        <div style="font-size:0.62rem;font-weight:600;letter-spacing:0.12em;text-transform:uppercase;
                    color:{MUTED};margin:24px 0 10px;font-family:'Lora',serif;">
          My Resolutions
        </div>""", unsafe_allow_html=True)

    for idx, g in enumerate(goals):
        dot   = DOTS[idx % len(DOTS)]
        is_active = g["id"] == st.session_state.selected_id
        stk   = f"&nbsp;&nbsp;🔥 {g['streak']}d" if g["streak"] > 0 else ""
        fw    = "600" if is_active else "400"
        bg    = ACTIVE if is_active else "transparent"

        if is_active:
            # Active goal: render as styled HTML div (non-button)
            st.markdown(f"""
            <div style="background:{ACTIVE};border-radius:10px;padding:11px 14px;
                        margin-bottom:4px;display:flex;align-items:center;
                        justify-content:space-between;cursor:default;">
              <div style="display:flex;align-items:center;gap:10px;">
                <div style="width:9px;height:9px;border-radius:50%;background:{dot};flex-shrink:0;"></div>
                <span style="color:{DARK};font-size:0.9rem;font-weight:600;
                             font-family:'Lora',serif;">{g['name']}</span>
              </div>
              <span style="font-size:0.76rem;color:{PRIMARY};">{stk.strip()}</span>
            </div>""", unsafe_allow_html=True)
        else:
            # Inactive: real clickable button
            st.markdown('<div class="btn-goal">', unsafe_allow_html=True)
            label = f"○  {g['name']}{'  ' + ('🔥 ' + str(g['streak']) + 'd') if g['streak'] > 0 else ''}"
            if st.button(label, key=f"sel_{g['id']}", use_container_width=True):
                st.session_state.selected_id = g["id"]
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    if not goals:
        st.markdown(f"""
        <div style="text-align:center;padding:40px 10px;color:{MUTED};">
          <div style="margin-bottom:12px;">{circle_svg(MUTED, 44)}</div>
          <div style="font-size:0.9rem;font-family:'Lora',serif;">No goals yet.</div>
          <div style="font-size:0.82rem;font-style:italic;margin-top:4px;
                      font-family:'Lora',serif;">Create your first resolution!</div>
        </div>""", unsafe_allow_html=True)


# ════════════════════════════════════════
# MIDDLE — goal detail
# ════════════════════════════════════════
with mid:
    if not sg:
        # Welcome screen (Image 3 style, purple)
        st.markdown(f"""
        <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;
                    min-height:75vh;text-align:center;padding:40px 20px;">
          <div style="width:110px;height:110px;border-radius:50%;background:rgba(255,220,190,0.5);
                      display:flex;align-items:center;justify-content:center;margin-bottom:28px;">
            {circle_svg(PRIMARY, 64)}
          </div>
          <h2 style="color:{DARK};font-size:2rem;margin:0 0 14px;font-weight:600;
                     font-family:'Lora',serif;letter-spacing:-0.02em;">
            Welcome to Your Resolution Tracker
          </h2>
          <p style="color:{MUTED};font-size:1rem;max-width:480px;line-height:1.65;margin:0 0 28px;
                    font-family:'Lora',serif;font-style:italic;">
            Start by creating your first goal. Your AI companion will guide you with
            personalized insights, research-backed tips, and weekly check-ins.
          </p>
        </div>""", unsafe_allow_html=True)


    else:
        goal_idx   = next((i for i, g in enumerate(goals) if g["id"] == sg["id"]), 0)
        goal_color = DOTS[goal_idx % len(DOTS)]

        # ── Header ──────────────────────────────────────
        created_str = ""
        try:
            d = datetime.fromisoformat(str(sg["created_at"]))
            created_str = f"Added {d.strftime('%b %-d')}"
        except Exception:
            pass
        freq_str = sg["frequency"].capitalize() if sg["frequency"] else ""
        target_str = (f"Target: {int(sg['target'])} {sg['unit']} · {freq_str}"
                      if sg["target"] and sg["unit"] else freq_str)
        meta = "  ·  ".join(p for p in [created_str, target_str] if p)

        # single div instead of st.columns — nested columns add unwanted vertical space
        streak_badge = (
            f'<div style="background:rgba(255,240,220,0.85);border:1px solid #E8C8A8;border-radius:20px;'
            f'padding:7px 14px;font-size:0.8rem;color:{PRIMARY};font-weight:600;'
            f'white-space:nowrap;font-family:\'Lora\',serif;flex-shrink:0;'
            f'backdrop-filter:blur(8px);">🔥 {sg["streak"]} day streak</div>'
            if sg["streak"] > 0 else ""
        )
        st.markdown(f"""
        <div style="display:flex;align-items:center;justify-content:space-between;gap:12px;padding:4px 0 8px;">
          <div style="display:flex;align-items:center;gap:14px;">
            <div style="width:50px;height:50px;border-radius:14px;background:{goal_color}22;
                        display:flex;align-items:center;justify-content:center;flex-shrink:0;">
              {circle_svg(goal_color, 30)}
            </div>
            <div>
              <div style="font-size:1.5rem;font-weight:600;color:{DARK};letter-spacing:-0.02em;
                          font-family:'Lora',serif;">{sg['name']}</div>
              <div style="font-size:0.78rem;color:{MUTED};margin-top:3px;font-family:'Lora',serif;">
                {meta}
              </div>
            </div>
          </div>
          {streak_badge}
        </div>""", unsafe_allow_html=True)

        st.markdown(f"<hr style='border:none;border-top:1px solid {BORDER};margin:14px 0;'>",
                    unsafe_allow_html=True)

        # ── This week ────────────────────────────────────
        days    = week_status(sg["logged_dates"])
        wk_cnt  = week_count(sg["logs"])
        tgt_wk  = int(sg["target"]) if sg["target"] else 7
        unit_l  = sg["unit"] or "logs"

        st.markdown(f'<div style="font-size:0.62rem;font-weight:600;letter-spacing:0.12em;'
                    f'text-transform:uppercase;color:{MUTED};font-family:\'Lora\',serif;'
                    f'margin-bottom:8px;">This Week</div>', unsafe_allow_html=True)

        # inline styles here because css classes don't reliably apply across separate st.markdown calls
        circle_styles = {
            "done":    f"background:{PRIMARY};color:white;",
            "today_y": f"background:{DARK};color:white;",
            "today_n": f"background:{DARK};color:{MUTED};font-size:0.65rem;",
            "missed":  "background:rgba(220,180,160,0.3);color:#A07880;",
            "future":  "background:rgba(220,200,180,0.2);color:#C8A898;",
        }
        circles = ""
        for d in days:
            if d["future"]:
                sty, txt = circle_styles["future"], "–"
            elif d["today"] and d["logged"]:
                sty, txt = circle_styles["today_y"], "✓"
            elif d["today"]:
                sty, txt = circle_styles["today_n"], "td"
            elif d["logged"]:
                sty, txt = circle_styles["done"], "✓"
            else:
                sty, txt = circle_styles["missed"], "–"
            circles += (
                f'<div style="display:flex;flex-direction:column;align-items:center;gap:5px;">'
                f'<div style="font-size:0.7rem;color:{MUTED};font-family:\'Lora\',serif;">{d["letter"]}</div>'
                f'<div style="width:38px;height:38px;border-radius:50%;display:flex;align-items:center;'
                f'justify-content:center;font-size:0.82rem;font-family:\'Lora\',serif;{sty}">{txt}</div>'
                f'</div>'
            )
        st.markdown(f'<div style="display:flex;gap:8px;margin:12px 0;">{circles}</div>',
                    unsafe_allow_html=True)

        pct = min(100, round(wk_cnt / max(1, tgt_wk) * 100))
        st.markdown(f"""
        <div style="display:flex;justify-content:space-between;margin:14px 0 6px;">
          <span style="font-size:0.875rem;color:{DARK};font-family:'Lora',serif;">Weekly progress</span>
          <span style="font-size:0.875rem;color:{PRIMARY};font-weight:600;
                       font-family:'Lora',serif;">{wk_cnt} / {tgt_wk} {unit_l}</span>
        </div>
        <div style="background:rgba(220,180,150,0.35);border-radius:8px;height:7px;overflow:hidden;">
          <div style="background:{PRIMARY};width:{pct}%;height:7px;border-radius:8px;transition:width 0.4s;"></div>
        </div>""", unsafe_allow_html=True)

        # single flexbox row instead of st.columns — avoids the huge gap streamlit adds below column groups
        def stat_card(num, lbl, clr):
            return (
                f'<div style="flex:1;background:white;border-radius:16px;padding:18px 12px;'
                f'text-align:center;border:1px solid {BORDER};box-shadow:0 2px 8px rgba(180,100,80,0.10);">'
                f'<div style="font-size:1.7rem;font-weight:600;color:{clr};line-height:1;'
                f'font-family:\'Lora\',serif;">{num}</div>'
                f'<div style="font-size:0.72rem;color:{MUTED};margin-top:5px;'
                f'font-family:\'Lora\',serif;">{lbl}</div>'
                f'</div>'
            )
        st.markdown(f"""
        <div style="display:flex;gap:12px;margin:16px 0;">
          {stat_card(sg['total_logs'], f'total {unit_l}', STAT1)}
          {stat_card(f"{sg['consistency']}%", 'consistency', STAT2)}
          {stat_card(sg['best_streak'], 'best streak', STAT3)}
        </div>""", unsafe_allow_html=True)

        # ── 6-week chart ──────────────────────────────────
        st.markdown(f'<div style="font-size:0.62rem;font-weight:600;letter-spacing:0.12em;'
                    f'text-transform:uppercase;color:{MUTED};font-family:\'Lora\',serif;'
                    f'margin-bottom:8px;">Last 6 Weeks</div>', unsafe_allow_html=True)

        wd   = six_week_data(sg["logs"])
        lbls = [w[0] for w in wd]; vals = [w[1] for w in wd]
        maxv = max(vals) if any(v > 0 for v in vals) else 1
        clrs = [f"rgba(200,120,88,{0.2 + 0.8*(v/maxv)})" if v > 0 else "rgba(220,180,150,0.25)" for v in vals]

        fig = go.Figure(go.Bar(x=lbls, y=vals, marker_color=clrs,
                               hovertemplate="%{x}: %{y}<extra></extra>"))
        fig.update_layout(
            height=140, margin=dict(l=0, r=0, t=4, b=28),
            xaxis=dict(showgrid=False, zeroline=False,
                       tickfont=dict(family="Lora, Georgia, serif", size=10, color=MUTED)),
            yaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
            plot_bgcolor="white", paper_bgcolor="white", showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        # ── Journal entries ───────────────────────────────
        if sg["journals"]:
            st.markdown(f'<div style="font-size:0.62rem;font-weight:600;letter-spacing:0.12em;'
                        f'text-transform:uppercase;color:{MUTED};font-family:\'Lora\',serif;'
                        f'margin-bottom:8px;">Journal</div>', unsafe_allow_html=True)
            for e in sg["journals"]:
                ds = e["date"][:10] if e["date"] else ""
                st.markdown(f"""
                <div style="background:rgba(255,240,220,0.7);border-left:3px solid #E8A878;padding:10px 14px;
                            border-radius:0 10px 10px 0;margin-bottom:8px;font-size:0.875rem;
                            color:{DARK};line-height:1.5;font-family:'Lora',serif;">
                  <div style="font-size:0.68rem;color:{MUTED};font-family:'Lora',serif;
                              margin-bottom:4px;">{ds}</div>
                  {e['text']}
                </div>""", unsafe_allow_html=True)

        # ── Weekly check-in card ──────────────────────────
        st.markdown(f"""
        <div style="background:rgba(255,235,210,0.75);border-radius:16px;padding:20px 22px;
                    border:1px solid rgba(230,185,140,0.6);margin-top:8px;">
          <div style="font-size:0.875rem;font-weight:600;color:{PRIMARY};margin-bottom:8px;
                      font-family:'Lora',serif;">Weekly check-in prompt</div>
          <div style="font-size:0.875rem;color:#9A5848;font-style:italic;line-height:1.55;
                      font-family:'Lora',serif;">
            How did <em>{sg['name'].lower()}</em> feel this week?<br>
            Any obstacles or wins you want to reflect on?
          </div>
        </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="btn-soft">', unsafe_allow_html=True)
        if st.button("Start reflection", key="reflect_btn", use_container_width=True):
            prompt = (f"I want to do a weekly reflection for my goal: '{sg['name']}'. "
                      "Look at my journal entries and progress data, give me an honest "
                      "check-in, and ask me a couple of questions about how this week went.")
            chat["messages"].append({"role": "user", "content": prompt})
            with st.spinner("Generating reflection…"):
                resp, new_hist = run_agent(prompt, chat["history"])
            chat["history"] = new_hist
            chat["messages"].append({"role": "assistant", "content": resp})
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)


# ════════════════════════════════════════
# RIGHT — per-goal chat
# ════════════════════════════════════════
with right:
    goal_label = sg["name"].upper() if sg else "GENERAL"
    st.markdown(f"""
    <div style="font-size:0.62rem;font-weight:600;letter-spacing:0.12em;text-transform:uppercase;
                color:{MUTED};font-family:'Lora',serif;margin-bottom:16px;">
      Agent Chat&ensp;·&ensp;{goal_label}
    </div>""", unsafe_allow_html=True)

    # Message display
    st.markdown('<div style="max-height:62vh;overflow-y:auto;padding-right:4px;" id="chat-area">',
                unsafe_allow_html=True)

    if not chat["messages"]:
        intro = (f"I'm tracking <em>{sg['name']}</em> with you. "
                 "Log your progress here, journal how you're feeling, or ask me anything."
                 if sg else
                 "Hi! I'm Resi, your resolution companion. Tell me what you want to work on "
                 "this year — I'll ask a few questions to make your goal concrete, then help "
                 "you track it week by week.")
        st.markdown(f"""
        <div style="background:rgba(200,225,240,0.55);border-radius:14px;padding:12px 16px;margin-bottom:10px;
                    font-size:0.875rem;line-height:1.55;font-family:'Lora',serif;color:{DARK};">
          <div style="font-size:0.62rem;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;
                      color:{PRIMARY};margin-bottom:5px;font-family:'Lora',serif;">Resi</div>
          {intro}
        </div>""", unsafe_allow_html=True)

    for msg in chat["messages"]:
        if msg["role"] == "assistant":
            st.markdown(f"""
            <div style="background:rgba(200,225,240,0.55);border-radius:14px;padding:12px 16px;margin-bottom:10px;
                        font-size:0.875rem;line-height:1.55;font-family:'Lora',serif;color:{DARK};">
              <div style="font-size:0.62rem;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;
                          color:{PRIMARY};margin-bottom:5px;font-family:'Lora',serif;">Resi</div>
              {msg['content']}
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="background:rgba(230,175,140,0.45);border-radius:14px;padding:12px 16px;margin-bottom:10px;
                        font-size:0.875rem;line-height:1.55;font-family:'Lora',serif;
                        color:{DARK};text-align:right;">
              <div style="font-size:0.62rem;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;
                          color:#A05040;margin-bottom:5px;font-family:'Lora',serif;text-align:right;">You</div>
              {msg['content']}
            </div>""", unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    # Chat input
    if prompt := st.chat_input("Log progress, journal, or ask for tips…"):
        chat["messages"].append({"role": "user", "content": prompt})
        with st.spinner("Thinking…"):
            resp, new_hist = run_agent(prompt, chat["history"])
        chat["history"] = new_hist
        chat["messages"].append({"role": "assistant", "content": resp})
        st.rerun()
