import streamlit as st
import json
import os
import datetime
import uuid
import re
import math
from pathlib import Path

# ── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FlashForge · Smart Flashcard Engine",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:ital,wght@0,300;0,400;0,500;1,400&display=swap');

html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
.main { background: #07080f; }
[data-testid="stSidebar"] { background: #0b0d17; border-right: 1px solid #1a1f35; }
h1,h2,h3 { font-family: 'Syne', sans-serif !important; }

/* ── Card flip ── */
.scene { width:100%; perspective:1000px; margin:1rem 0; }
.card-wrap {
    position:relative; width:100%; height:260px;
    transform-style:preserve-3d;
    transition:transform 0.6s cubic-bezier(.4,0,.2,1);
}
.card-wrap.flipped { transform:rotateY(180deg); }
.card-front, .card-back {
    position:absolute; width:100%; height:100%;
    backface-visibility:hidden; border-radius:18px;
    display:flex; flex-direction:column;
    align-items:center; justify-content:center;
    padding:2rem; text-align:center;
}
.card-front {
    background:linear-gradient(135deg,#111827,#0f172a);
    border:1px solid #2d3a5a;
    box-shadow:0 8px 40px rgba(0,0,0,.6);
}
.card-back {
    background:linear-gradient(135deg,#0f2027,#0c1a2e);
    border:1px solid #1e4a7a;
    box-shadow:0 8px 40px rgba(30,74,122,.3);
    transform:rotateY(180deg);
}
.card-q { font-family:'Syne',sans-serif; font-size:1.25rem; font-weight:700; color:#e2e8f0; line-height:1.5; }
.card-a { font-size:1.05rem; color:#93c5fd; line-height:1.6; }
.card-hint { font-size:0.72rem; color:#374151; margin-top:1rem; text-transform:uppercase; letter-spacing:.1em; }
.card-label { font-size:0.7rem; font-weight:700; letter-spacing:.15em; text-transform:uppercase; margin-bottom:1rem; }
.card-label.q { color:#4f46e5; }
.card-label.a { color:#0891b2; }

/* ── Rating buttons ── */
.rating-row { display:flex; gap:12px; justify-content:center; margin-top:1.2rem; flex-wrap:wrap; }

/* ── Stat cards ── */
.stat-box {
    background:#0f172a; border:1px solid #1e293b; border-radius:14px;
    padding:1.2rem 1.4rem; text-align:center;
}
.stat-num { font-family:'Syne',sans-serif; font-size:2.4rem; font-weight:800; }
.stat-lbl { color:#475569; font-size:0.75rem; text-transform:uppercase; letter-spacing:.1em; margin-top:4px; }

/* ── Deck card ── */
.deck-card {
    background:#0f172a; border:1px solid #1e293b; border-radius:14px;
    padding:1.2rem 1.4rem; margin-bottom:.8rem; cursor:pointer;
    transition:border-color .2s;
}
.deck-card:hover { border-color:#3b82f6; }
.deck-title { font-family:'Syne',sans-serif; font-size:1.05rem; font-weight:700; color:#e2e8f0; }
.deck-meta  { color:#475569; font-size:0.78rem; margin-top:4px; }
.deck-bar-track { background:#1e293b; border-radius:6px; height:6px; margin-top:10px; }
.deck-bar-fill  { height:6px; border-radius:6px; }

/* ── Progress bar ── */
.prog-wrap { background:#1e293b; border-radius:8px; height:10px; overflow:hidden; margin:6px 0 2px; }
.prog-fill  { height:100%; border-radius:8px; }

/* ── Hero ── */
.hero-title {
    font-family:'Syne',sans-serif; font-size:2.5rem; font-weight:800;
    background:linear-gradient(135deg,#60a5fa 0%,#a78bfa 50%,#34d399 100%);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text;
}
.hero-sub { color:#475569; font-size:.95rem; margin-top:4px; }

/* ── General ── */
.section-title {
    font-family:'Syne',sans-serif; font-size:.9rem; font-weight:700;
    color:#e2e8f0; text-transform:uppercase; letter-spacing:.08em; margin:1.4rem 0 .7rem;
}
.pill {
    display:inline-block; padding:3px 12px; border-radius:50px;
    font-size:.72rem; font-weight:700; text-transform:uppercase; letter-spacing:.08em;
}
.pill-green  { background:rgba(52,211,153,.12); color:#34d399; border:1px solid rgba(52,211,153,.25); }
.pill-yellow { background:rgba(251,191,36,.12);  color:#fbbf24; border:1px solid rgba(251,191,36,.25); }
.pill-red    { background:rgba(248,113,113,.12); color:#f87171; border:1px solid rgba(248,113,113,.25); }
.pill-blue   { background:rgba(96,165,250,.12);  color:#60a5fa; border:1px solid rgba(96,165,250,.25); }

[data-testid="stSidebar"] label { color:#64748b !important; font-size:.8rem !important; }
</style>
""", unsafe_allow_html=True)

# ── SM-2 Algorithm ─────────────────────────────────────────────────────────────
def sm2_update(card, quality):
    """SM-2 spaced repetition. quality: 0=Again,1=Hard,3=Good,5=Easy"""
    ef = card.get("ease_factor", 2.5)
    reps = card.get("repetitions", 0)
    interval = card.get("interval", 1)

    if quality >= 3:
        if reps == 0:   interval = 1
        elif reps == 1: interval = 6
        else:           interval = round(interval * ef)
        reps += 1
    else:
        reps = 0
        interval = 1

    ef = max(1.3, ef + 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    due = (datetime.datetime.now() + datetime.timedelta(days=interval)).isoformat()

    card.update({"ease_factor": round(ef,2), "repetitions": reps,
                 "interval": interval, "due": due})
    # Status
    if reps >= 4 and interval >= 21: card["status"] = "mastered"
    elif reps >= 1:                  card["status"] = "learning"
    else:                            card["status"] = "new"
    return card

def is_due(card):
    due = card.get("due")
    if not due: return True
    return datetime.datetime.fromisoformat(due) <= datetime.datetime.now()

# ── Persistence (JSON file) ───────────────────────────────────────────────────
DATA_FILE = "flashforge_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except: pass
    return {"decks": {}}

def save_data(data):
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except: pass

# ── Session State Init ────────────────────────────────────────────────────────
if "data" not in st.session_state:
    st.session_state.data = load_data()
if "view" not in st.session_state:
    st.session_state.view = "home"          # home | study | deck_detail
if "active_deck" not in st.session_state:
    st.session_state.active_deck = None
if "study_queue" not in st.session_state:
    st.session_state.study_queue = []
if "study_idx" not in st.session_state:
    st.session_state.study_idx = 0
if "flipped" not in st.session_state:
    st.session_state.flipped = False
if "session_done" not in st.session_state:
    st.session_state.session_done = 0
if "session_total" not in st.session_state:
    st.session_state.session_total = 0

data = st.session_state.data

# ── Groq Card Generator ───────────────────────────────────────────────────────
def generate_cards(text, api_key, num_cards=15):
    from groq import Groq
    client = Groq(api_key=api_key)

    # Truncate to ~6000 chars to stay within context
    chunk = text[:6000]

    prompt = f"""You are an expert educator creating high-quality flashcards for active recall.

Given the following educational text, generate exactly {num_cards} flashcards as a JSON array.

Rules:
- Cover key concepts, definitions, relationships, formulas, and edge cases
- Questions should be specific and unambiguous
- Answers should be concise but complete (2-4 sentences max)
- Vary question types: definition, application, comparison, "why", "what happens when"
- Write like a great teacher, not a bot scraping text
- Do NOT include any markdown, just return raw JSON

Return ONLY this JSON (no extra text, no code fences):
[
  {{"question": "...", "answer": "..."}},
  ...
]

Text:
{chunk}"""

    resp = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role":"user","content":prompt}],
        max_tokens=2500,
        temperature=0.5,
    )
    raw = resp.choices[0].message.content.strip()
    # Strip code fences if present
    raw = re.sub(r"```json\s*|```\s*", "", raw).strip()
    cards_data = json.loads(raw)
    cards = []
    for i, cd in enumerate(cards_data):
        cards.append({
            "id": str(uuid.uuid4()),
            "question": cd["question"],
            "answer": cd["answer"],
            "ease_factor": 2.5,
            "repetitions": 0,
            "interval": 1,
            "due": None,
            "status": "new",
        })
    return cards

def extract_pdf_text(file):
    import pdfplumber
    text = ""
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t: text += t + "\n"
    return text.strip()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<p style="font-family:Syne,sans-serif;font-size:1.1rem;font-weight:800;color:#60a5fa;margin-bottom:0;">⚡ FlashForge</p>', unsafe_allow_html=True)
    st.markdown('<p style="color:#334155;font-size:.72rem;margin-top:0;margin-bottom:1.2rem;">Smart Flashcard Engine · Cuemath</p>', unsafe_allow_html=True)

    # Nav
    if st.button("🏠  Home / All Decks", use_container_width=True):
        st.session_state.view = "home"
        st.rerun()

    st.markdown("---")
    st.markdown("**➕ Create New Deck**")
    api_key = st.text_input("Groq API Key", type="password", placeholder="gsk_...", key="api_key_input")
    pdf_file = st.file_uploader("Upload PDF", type=["pdf"])
    deck_name = st.text_input("Deck Name", placeholder="e.g. Chapter 3 — Quadratics")
    num_cards = st.slider("Cards to generate", 8, 25, 15)

    if st.button("⚡ Generate Flashcards", use_container_width=True, type="primary"):
        if not api_key:
            st.error("Enter your Groq API key.")
        elif not pdf_file:
            st.error("Upload a PDF first.")
        elif not deck_name.strip():
            st.error("Name your deck.")
        else:
            with st.spinner("Reading PDF..."):
                try:
                    pdf_text = extract_pdf_text(pdf_file)
                except Exception as e:
                    st.error(f"PDF error: {e}")
                    st.stop()

            if len(pdf_text) < 100:
                st.error("PDF has too little text. Try a different file.")
            else:
                with st.spinner(f"Generating {num_cards} flashcards with AI..."):
                    try:
                        cards = generate_cards(pdf_text, api_key, num_cards)
                        deck_id = str(uuid.uuid4())
                        data["decks"][deck_id] = {
                            "id": deck_id,
                            "name": deck_name.strip(),
                            "created": datetime.datetime.now().isoformat(),
                            "source": pdf_file.name,
                            "cards": cards,
                        }
                        save_data(data)
                        st.session_state.active_deck = deck_id
                        st.session_state.view = "deck_detail"
                        st.success(f"✅ {len(cards)} cards created!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Generation failed: {e}")

    st.markdown("---")
    # Deck list
    if data["decks"]:
        st.markdown("**Your Decks**")
        for did, dk in data["decks"].items():
            cards = dk["cards"]
            due_count = sum(1 for c in cards if is_due(c))
            label = f"{'🔴 ' if due_count else ''}{dk['name']} ({due_count} due)"
            if st.button(label, key=f"nav_{did}", use_container_width=True):
                st.session_state.active_deck = did
                st.session_state.view = "deck_detail"
                st.rerun()

# ── MAIN ──────────────────────────────────────────────────────────────────────

# ════════════════════ HOME VIEW ════════════════════════════════════════════════
if st.session_state.view == "home":
    st.markdown('<h1 class="hero-title">FlashForge</h1>', unsafe_allow_html=True)
    st.markdown('<p class="hero-sub">Drop in a PDF. Get smart flashcards. Master anything.</p>', unsafe_allow_html=True)

    if not data["decks"]:
        # Empty state
        st.markdown("<br>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        for col, icon, title, desc in [
            (c1, "📄", "Upload any PDF", "Textbook chapters, class notes, research papers — anything."),
            (c2, "🤖", "AI writes your cards", "LLaMA 3.3 70B generates cards that cover concepts, definitions, and edge cases."),
            (c3, "🧠", "Spaced repetition", "SM-2 algorithm shows struggling cards more often. Mastery guaranteed."),
        ]:
            col.markdown(f"""<div style="background:#0f172a;border:1px solid #1e293b;border-radius:14px;padding:1.6rem;text-align:center;">
            <div style="font-size:2rem;margin-bottom:12px;">{icon}</div>
            <div style="font-family:Syne,sans-serif;font-weight:700;color:#e2e8f0;margin-bottom:8px;">{title}</div>
            <div style="color:#475569;font-size:.85rem;line-height:1.6;">{desc}</div>
            </div>""", unsafe_allow_html=True)
        st.markdown('<p style="color:#1e293b;text-align:center;font-size:.8rem;margin-top:2rem;">Upload a PDF in the sidebar to get started →</p>', unsafe_allow_html=True)
        st.stop()

    # Stats row
    all_cards = [c for dk in data["decks"].values() for c in dk["cards"]]
    total     = len(all_cards)
    mastered  = sum(1 for c in all_cards if c["status"] == "mastered")
    learning  = sum(1 for c in all_cards if c["status"] == "learning")
    due_all   = sum(1 for c in all_cards if is_due(c))
    pct       = round(mastered / total * 100) if total else 0

    col1, col2, col3, col4 = st.columns(4)
    for col, num, label, color in [
        (col1, total,    "Total Cards",    "#60a5fa"),
        (col2, mastered, "Mastered",       "#34d399"),
        (col3, learning, "In Progress",    "#fbbf24"),
        (col4, due_all,  "Due for Review", "#f87171"),
    ]:
        col.markdown(f"""<div class="stat-box">
        <div class="stat-num" style="color:{color};">{num}</div>
        <div class="stat-lbl">{label}</div>
        </div>""", unsafe_allow_html=True)

    # Overall progress
    if total:
        st.markdown(f"""<div style="margin:1.2rem 0 .3rem;">
        <div style="display:flex;justify-content:space-between;color:#475569;font-size:.75rem;margin-bottom:4px;">
            <span>Overall Mastery</span><span style="color:#34d399;font-weight:600;">{pct}%</span>
        </div>
        <div class="prog-wrap"><div class="prog-fill" style="width:{pct}%;background:linear-gradient(90deg,#34d399,#60a5fa);"></div></div>
        </div>""", unsafe_allow_html=True)

    st.markdown('<div class="section-title">📚 Your Decks</div>', unsafe_allow_html=True)

    for did, dk in data["decks"].items():
        cards  = dk["cards"]
        total_d = len(cards)
        mast_d  = sum(1 for c in cards if c["status"] == "mastered")
        due_d   = sum(1 for c in cards if is_due(c))
        pct_d   = round(mast_d / total_d * 100) if total_d else 0
        created = dk["created"][:10]

        col_d, col_btn = st.columns([5, 1])
        with col_d:
            st.markdown(f"""<div class="deck-card">
            <div style="display:flex;align-items:center;gap:10px;">
                <div class="deck-title">{dk['name']}</div>
                {'<span class="pill pill-red">'+str(due_d)+' due</span>' if due_d else '<span class="pill pill-green">Up to date</span>'}
            </div>
            <div class="deck-meta">📄 {dk['source']}  ·  {total_d} cards  ·  created {created}</div>
            <div class="deck-bar-track">
                <div class="deck-bar-fill" style="width:{pct_d}%;background:linear-gradient(90deg,#34d399,#60a5fa);"></div>
            </div>
            <div style="display:flex;justify-content:space-between;font-size:.72rem;color:#334155;margin-top:4px;">
                <span>{mast_d} mastered</span><span>{pct_d}% complete</span>
            </div>
            </div>""", unsafe_allow_html=True)
        with col_btn:
            st.markdown("<br><br>", unsafe_allow_html=True)
            if st.button("Study →", key=f"study_{did}", type="primary"):
                st.session_state.active_deck = did
                st.session_state.view = "deck_detail"
                st.rerun()


# ════════════════════ DECK DETAIL ══════════════════════════════════════════════
elif st.session_state.view == "deck_detail":
    did = st.session_state.active_deck
    if not did or did not in data["decks"]:
        st.session_state.view = "home"; st.rerun()

    dk    = data["decks"][did]
    cards = dk["cards"]
    total_d = len(cards)
    mast_d  = sum(1 for c in cards if c["status"] == "mastered")
    learn_d = sum(1 for c in cards if c["status"] == "learning")
    new_d   = sum(1 for c in cards if c["status"] == "new")
    due_d   = [c for c in cards if is_due(c)]
    pct_d   = round(mast_d / total_d * 100) if total_d else 0

    # Header
    col_hd, col_del = st.columns([8,1])
    with col_hd:
        st.markdown(f'<h2 style="font-family:Syne,sans-serif;color:#e2e8f0;margin-bottom:4px;">{dk["name"]}</h2>', unsafe_allow_html=True)
        st.markdown(f'<p style="color:#475569;font-size:.85rem;">📄 {dk["source"]}  ·  {total_d} cards</p>', unsafe_allow_html=True)
    with col_del:
        if st.button("🗑️ Delete", key="del_deck"):
            del data["decks"][did]
            save_data(data)
            st.session_state.view = "home"
            st.rerun()

    # Progress bars
    c1,c2,c3,c4 = st.columns(4)
    for col, num, label, color in [
        (c1, mast_d,  "Mastered",    "#34d399"),
        (c2, learn_d, "Learning",    "#fbbf24"),
        (c3, new_d,   "New",         "#60a5fa"),
        (c4, len(due_d), "Due Now",  "#f87171"),
    ]:
        col.markdown(f"""<div class="stat-box">
        <div class="stat-num" style="color:{color};">{num}</div>
        <div class="stat-lbl">{label}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown(f"""<div style="margin:1rem 0 .3rem;">
    <div style="display:flex;justify-content:space-between;color:#475569;font-size:.75rem;margin-bottom:4px;">
        <span>Deck Mastery</span><span style="color:#34d399;font-weight:600;">{pct_d}%</span>
    </div>
    <div class="prog-wrap"><div class="prog-fill" style="width:{pct_d}%;background:linear-gradient(90deg,#34d399,#60a5fa);"></div></div>
    </div>""", unsafe_allow_html=True)

    # Start study button
    st.markdown("<br>", unsafe_allow_html=True)
    col_btn1, col_btn2, _ = st.columns([1,1,3])
    with col_btn1:
        btn_label = f"🧠 Study Due Cards ({len(due_d)})" if due_d else "✅ All caught up!"
        if st.button(btn_label, use_container_width=True, type="primary", disabled=not due_d):
            st.session_state.study_queue = [c["id"] for c in due_d]
            random.shuffle(st.session_state.study_queue)
            st.session_state.study_idx = 0
            st.session_state.flipped = False
            st.session_state.session_done = 0
            st.session_state.session_total = len(due_d)
            st.session_state.view = "study"
            st.rerun()
    with col_btn2:
        if st.button("🔀 Study All Cards", use_container_width=True):
            all_ids = [c["id"] for c in cards]
            random.shuffle(all_ids)
            st.session_state.study_queue = all_ids
            st.session_state.study_idx = 0
            st.session_state.flipped = False
            st.session_state.session_done = 0
            st.session_state.session_total = len(all_ids)
            st.session_state.view = "study"
            st.rerun()

    # Card list
    st.markdown('<div class="section-title">📋 All Cards</div>', unsafe_allow_html=True)
    for i, card in enumerate(cards):
        status_pill = {
            "mastered": '<span class="pill pill-green">Mastered</span>',
            "learning": '<span class="pill pill-yellow">Learning</span>',
            "new":      '<span class="pill pill-blue">New</span>',
        }.get(card["status"], "")
        due_str = ""
        if card.get("due"):
            due_dt = datetime.datetime.fromisoformat(card["due"])
            diff = (due_dt - datetime.datetime.now()).days
            due_str = f"  ·  due {'today' if diff <= 0 else f'in {diff}d'}"

        with st.expander(f"Q{i+1}: {card['question'][:70]}{'...' if len(card['question'])>70 else ''}"):
            st.markdown(f"**Q:** {card['question']}")
            st.markdown(f"**A:** {card['answer']}")
            st.markdown(f"{status_pill} &nbsp; interval: {card.get('interval',1)}d{due_str}", unsafe_allow_html=True)


# ════════════════════ STUDY VIEW ═══════════════════════════════════════════════
elif st.session_state.view == "study":
    did   = st.session_state.active_deck
    dk    = data["decks"][did]
    cards = dk["cards"]
    queue = st.session_state.study_queue
    idx   = st.session_state.study_idx

    if idx >= len(queue):
        # Session complete
        st.markdown('<h2 style="font-family:Syne,sans-serif;color:#34d399;text-align:center;margin-top:3rem;">🎉 Session Complete!</h2>', unsafe_allow_html=True)
        st.markdown(f'<p style="text-align:center;color:#64748b;">You reviewed {st.session_state.session_done} cards.</p>', unsafe_allow_html=True)
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("📚 Back to Deck", use_container_width=True, type="primary"):
                st.session_state.view = "deck_detail"
                st.rerun()
        with col_b:
            if st.button("🏠 Home", use_container_width=True):
                st.session_state.view = "home"
                st.rerun()
        st.stop()

    # Find current card
    cid = queue[idx]
    card = next((c for c in cards if c["id"] == cid), None)
    if not card:
        st.session_state.study_idx += 1
        st.rerun()

    # Progress bar
    prog = idx / len(queue)
    st.markdown(f"""<div style="margin-bottom:1rem;">
    <div style="display:flex;justify-content:space-between;color:#475569;font-size:.75rem;margin-bottom:4px;">
        <span>← <a href="#" style="color:#475569;text-decoration:none;" onclick="">Back</a></span>
        <span style="color:#e2e8f0;font-weight:600;">{idx+1} / {len(queue)}</span>
        <span>{st.session_state.session_done} done</span>
    </div>
    <div class="prog-wrap"><div class="prog-fill" style="width:{prog*100:.1f}%;background:linear-gradient(90deg,#4f46e5,#7c3aed);"></div></div>
    </div>""", unsafe_allow_html=True)

    # Deck name
    st.markdown(f'<p style="color:#334155;font-size:.78rem;margin-bottom:.5rem;">📚 {dk["name"]}</p>', unsafe_allow_html=True)

    flipped = st.session_state.flipped

    # Card HTML
    flip_class = "card-wrap flipped" if flipped else "card-wrap"
    st.markdown(f"""
    <div class="scene">
        <div class="{flip_class}">
            <div class="card-front">
                <div class="card-label q">Question</div>
                <div class="card-q">{card['question']}</div>
                <div class="card-hint">{'Click Reveal Answer ↓' if not flipped else ''}</div>
            </div>
            <div class="card-back">
                <div class="card-label a">Answer</div>
                <div class="card-a">{card['answer']}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if not flipped:
        col_flip, _ = st.columns([2,5])
        with col_flip:
            if st.button("👁️ Reveal Answer", use_container_width=True, type="primary"):
                st.session_state.flipped = True
                st.rerun()
    else:
        # Rating buttons
        st.markdown('<p style="color:#475569;font-size:.8rem;text-align:center;margin-top:.5rem;">How well did you know this?</p>', unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)
        ratings = [
            (c1, "😵 Again",  0, "#f87171"),
            (c2, "😓 Hard",   2, "#fbbf24"),
            (c3, "🙂 Good",   3, "#60a5fa"),
            (c4, "😎 Easy",   5, "#34d399"),
        ]
        for col, label, quality, color in ratings:
            with col:
                if st.button(label, use_container_width=True, key=f"rate_{quality}"):
                    # Update card
                    updated = sm2_update(dict(card), quality)
                    for i_c, c in enumerate(dk["cards"]):
                        if c["id"] == cid:
                            dk["cards"][i_c] = updated
                            break
                    save_data(data)
                    st.session_state.session_done += 1
                    st.session_state.study_idx += 1
                    st.session_state.flipped = False
                    st.rerun()

        col_skip, _ = st.columns([1,5])
        with col_skip:
            if st.button("⏭️ Skip", key="skip_card"):
                st.session_state.study_idx += 1
                st.session_state.flipped = False
                st.rerun()

    # Back button
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("← Back to Deck"):
        st.session_state.view = "deck_detail"
        st.rerun()

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown('<hr style="border:none;border-top:1px solid #0f172a;margin-top:3rem;">', unsafe_allow_html=True)
st.markdown('<p style="color:#0f172a;text-align:center;font-size:.7rem;">FlashForge · Cuemath AI Builder Challenge · SM-2 Spaced Repetition · Built with Groq + LLaMA 3.3 70B</p>', unsafe_allow_html=True)
