"""
=============================================================
             AXIOM — STREAMLIT HABIT TRACKER
=============================================================
Features:
  - Add & customize new habits (name, category, emoji, description)
  - Daily check-in dashboard with interactive completion toggle
  - Date selector to inspect or backfill completions
  - Real-time streak calculation (Current Streak & Best Streak)
  - Interactive Weekly Consistency Matrix (Mon-Sun)
  - Habit leaderboard & 30-day consistency analytics
  - Manage and delete habits
  - Robust local SQLite persistence (habits.db)
=============================================================
"""

import os
import sqlite3
from datetime import datetime, date, timedelta
import streamlit as st

# -------------------------------------------------------------
# Database Setup & Helpers
# -------------------------------------------------------------
DB_PATH = os.path.join(os.path.dirname(__file__), "habits.db")


def get_db_connection():
    """Returns a connection to the SQLite database with Row factory."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Initializes SQLite tables and seeds starter habits if empty."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Habits table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS habits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            category TEXT DEFAULT 'General',
            icon TEXT DEFAULT '✨',
            created_at TEXT NOT NULL,
            archived INTEGER DEFAULT 0
        )
    """)

    # Habit completion logs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS habit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            habit_id INTEGER NOT NULL,
            completed_date TEXT NOT NULL,
            notes TEXT,
            UNIQUE(habit_id, completed_date),
            FOREIGN KEY(habit_id) REFERENCES habits(id) ON DELETE CASCADE
        )
    """)
    conn.commit()

    # Seed starter habits if database is brand new
    cursor.execute("SELECT COUNT(*) AS count FROM habits")
    if cursor.fetchone()["count"] == 0:
        samples = [
            ("Morning Workout", "30 mins cardio or strength training", "Fitness", "🏋️"),
            ("Drink 2L Water", "Stay hydrated throughout the day", "Health", "💧"),
            ("Read 20 Minutes", "Read non-fiction or literature", "Learning", "📚"),
            ("Mindful Meditation", "10 minutes guided breathing", "Mindfulness", "🧘"),
            ("Deep Work Session", "Focus block with zero distractions", "Productivity", "💻"),
        ]
        today = date.today()
        for name, desc, cat, icon in samples:
            cursor.execute("""
                INSERT INTO habits (name, description, category, icon, created_at, archived)
                VALUES (?, ?, ?, ?, ?, 0)
            """, (name, desc, cat, icon, (today - timedelta(days=14)).isoformat()))
            habit_id = cursor.lastrowid

            # Seed a few days of completions to show live streaks
            for past_days in [0, 1, 2, 4, 5, 7, 8, 9]:
                log_date = (today - timedelta(days=past_days)).isoformat()
                cursor.execute("""
                    INSERT OR IGNORE INTO habit_logs (habit_id, completed_date)
                    VALUES (?, ?)
                """, (habit_id, log_date))

        conn.commit()

    conn.close()


# -------------------------------------------------------------
# Data Access & Business Logic
# -------------------------------------------------------------
def get_all_habits(include_archived=False):
    """Retrieve habits from SQLite."""
    conn = get_db_connection()
    if include_archived:
        rows = conn.execute("SELECT * FROM habits ORDER BY id ASC").fetchall()
    else:
        rows = conn.execute("SELECT * FROM habits WHERE archived = 0 ORDER BY id ASC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_habit(name, description, category, icon):
    """Adds a new habit to the database."""
    conn = get_db_connection()
    try:
        conn.execute("""
            INSERT INTO habits (name, description, category, icon, created_at, archived)
            VALUES (?, ?, ?, ?, ?, 0)
        """, (name.strip(), description.strip(), category, icon, date.today().isoformat()))
        conn.commit()
        return True, "Habit added successfully!"
    except sqlite3.IntegrityError:
        return False, f"A habit named '{name}' already exists."
    finally:
        conn.close()


def delete_habit(habit_id):
    """Deletes a habit and all associated logs."""
    conn = get_db_connection()
    conn.execute("DELETE FROM habits WHERE id = ?", (habit_id,))
    conn.commit()
    conn.close()


def toggle_habit_completion(habit_id, target_date: date):
    """Toggles completion status for a habit on a given date."""
    date_str = target_date.isoformat()
    conn = get_db_connection()
    existing = conn.execute("""
        SELECT id FROM habit_logs WHERE habit_id = ? AND completed_date = ?
    """, (habit_id, date_str)).fetchone()

    if existing:
        conn.execute("DELETE FROM habit_logs WHERE id = ?", (existing["id"],))
        completed = False
    else:
        conn.execute("""
            INSERT INTO habit_logs (habit_id, completed_date)
            VALUES (?, ?)
        """, (habit_id, date_str))
        completed = True

    conn.commit()
    conn.close()
    return completed


def get_completed_habit_ids_for_date(target_date: date) -> set:
    """Returns set of habit_ids completed on target_date."""
    conn = get_db_connection()
    rows = conn.execute("""
        SELECT habit_id FROM habit_logs WHERE completed_date = ?
    """, (target_date.isoformat(),)).fetchall()
    conn.close()
    return {r["habit_id"] for r in rows}


def get_all_completion_dates_for_habit(habit_id: int) -> set:
    """Returns set of date objects when habit was completed."""
    conn = get_db_connection()
    rows = conn.execute("""
        SELECT completed_date FROM habit_logs WHERE habit_id = ? ORDER BY completed_date ASC
    """, (habit_id,)).fetchall()
    conn.close()
    dates = set()
    for r in rows:
        try:
            dates.add(datetime.strptime(r["completed_date"], "%Y-%m-%d").date())
        except ValueError:
            pass
    return dates


def calculate_streaks(habit_id: int) -> dict:
    """
    Calculates current streak, longest streak, and total completions for a habit.
    """
    dates = get_all_completion_dates_for_habit(habit_id)
    if not dates:
        return {"current_streak": 0, "longest_streak": 0, "total_completions": 0}

    sorted_dates = sorted(dates)
    total_completions = len(sorted_dates)

    # 1. Calculate Longest Streak
    longest_streak = 0
    current_calc_streak = 0
    prev_date = None

    for d in sorted_dates:
        if prev_date is None:
            current_calc_streak = 1
        elif d == prev_date + timedelta(days=1):
            current_calc_streak += 1
        else:
            current_calc_streak = 1
        longest_streak = max(longest_streak, current_calc_streak)
        prev_date = d

    # 2. Calculate Current Streak
    today = date.today()
    yesterday = today - timedelta(days=1)

    current_streak = 0
    if today in dates:
        check_date = today
    elif yesterday in dates:
        check_date = yesterday
    else:
        check_date = None

    if check_date:
        while check_date in dates:
            current_streak += 1
            check_date -= timedelta(days=1)

    return {
        "current_streak": current_streak,
        "longest_streak": max(longest_streak, current_streak),
        "total_completions": total_completions
    }


def get_daily_completion_counts(days=30) -> list[dict]:
    """Returns daily count of completed habits for the past N days."""
    conn = get_db_connection()
    start_date = (date.today() - timedelta(days=days)).isoformat()
    rows = conn.execute("""
        SELECT completed_date, COUNT(*) AS count
        FROM habit_logs
        WHERE completed_date >= ?
        GROUP BY completed_date
        ORDER BY completed_date ASC
    """, (start_date,)).fetchall()
    conn.close()
    return [{"date": r["completed_date"], "count": r["count"]} for r in rows]


def get_completions_by_category() -> dict:
    """Returns completions breakdown grouped by category."""
    conn = get_db_connection()
    rows = conn.execute("""
        SELECT h.category, COUNT(l.id) AS count
        FROM habits h
        LEFT JOIN habit_logs l ON h.id = l.habit_id
        GROUP BY h.category
    """).fetchall()
    conn.close()
    return {r["category"]: r["count"] for r in rows}


# -------------------------------------------------------------
# Streamlit Application UI
# -------------------------------------------------------------
def main():
    st.set_page_config(
        page_title="AXIOM — Habit Tracker",
        page_icon="🔥",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Initialize DB
    init_db()

    # Custom styling
    st.markdown("""
        <style>
        .badge-cat {
            background-color: #2563eb;
            color: #ffffff;
            padding: 3px 10px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
        }
        .streak-pill {
            background-color: #f97316;
            color: #ffffff;
            padding: 3px 10px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
        }
        </style>
    """, unsafe_allow_html=True)

    # Sidebar: Add Habit & Date Selection
    with st.sidebar:
        st.title("🔥 AXIOM Habit Tracker")
        st.caption("Build consistency. Master your day.")
        st.divider()

        # Date Picker for Daily View
        st.subheader("📅 Check-in Date")
        selected_date = st.date_input("Select Date", value=date.today())
        is_today = (selected_date == date.today())
        date_label = "Today" if is_today else selected_date.strftime("%b %d, %Y")

        st.divider()

        # Add New Habit Form
        st.subheader("➕ Add New Habit")
        with st.form("new_habit_form", clear_on_submit=True):
            h_name = st.text_input("Habit Name*", placeholder="e.g. 10,000 Steps")
            h_cat = st.selectbox(
                "Category",
                ["Health", "Fitness", "Learning", "Productivity", "Mindfulness", "Finance", "Other"]
            )
            h_icon = st.selectbox(
                "Icon / Emoji",
                ["🔥", "🏋️", "💧", "📚", "🧘", "💻", "🥗", "🎯", "🚶", "✍️", "💰", "😴", "✨"]
            )
            h_desc = st.text_input("Description (optional)", placeholder="e.g. Daily morning walk")

            submitted = st.form_submit_button("Add Habit", use_container_width=True)
            if submitted:
                if not h_name.strip():
                    st.error("Please enter a habit name.")
                else:
                    success, msg = add_habit(h_name, h_desc, h_cat, h_icon)
                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

        st.divider()
        st.caption("Local SQLite storage: `habits.db`")

    # Main Navigation Tabs
    tab_dashboard, tab_weekly, tab_analytics, tab_manage = st.tabs([
        "📋 Daily Check-in",
        "🗓️ Weekly Matrix",
        "📊 Progress & Analytics",
        "⚙️ Manage Habits"
    ])

    habits = get_all_habits()

    if not habits:
        st.info("No active habits found. Use the sidebar on the left to add your first habit!")
        return

    # -------------------------------------------------------------
    # TAB 1: Daily Check-in Dashboard
    # -------------------------------------------------------------
    with tab_dashboard:
        completed_ids = get_completed_habit_ids_for_date(selected_date)
        total_count = len(habits)
        done_count = len([h for h in habits if h["id"] in completed_ids])
        pct_done = int((done_count / total_count) * 100) if total_count > 0 else 0

        # Top Summary Metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Habits", total_count)
        with col2:
            st.metric(f"Completed ({date_label})", f"{done_count} / {total_count}")
        with col3:
            st.metric("Completion Rate", f"{pct_done}%")
        with col4:
            active_streaks = [calculate_streaks(h["id"])["current_streak"] for h in habits]
            best_curr = max(active_streaks) if active_streaks else 0
            st.metric("Top Current Streak", f"🔥 {best_curr} days")

        # Progress bar
        st.progress(pct_done / 100.0)

        if done_count == total_count and total_count > 0:
            st.success(f"🎉 Fantastic job! All habits completed for {date_label}!")
            if is_today:
                st.balloons()

        st.subheader(f"Habits for {date_label}")

        # List of habits with completion checkboxes
        for habit in habits:
            h_id = habit["id"]
            is_done = h_id in completed_ids
            streak_info = calculate_streaks(h_id)

            card_col1, card_col2, card_col3, card_col4 = st.columns([0.08, 0.52, 0.25, 0.15])

            with card_col1:
                chk = st.checkbox(
                    "Done",
                    value=is_done,
                    key=f"chk_{h_id}_{selected_date}",
                    label_visibility="collapsed"
                )
                if chk != is_done:
                    toggle_habit_completion(h_id, selected_date)
                    st.rerun()

            with card_col2:
                st.markdown(f"**{habit['icon']} {habit['name']}** &nbsp; <span class='badge-cat'>{habit['category']}</span>", unsafe_allow_html=True)
                if habit["description"]:
                    st.caption(habit["description"])

            with card_col3:
                curr_s = streak_info["current_streak"]
                best_s = streak_info["longest_streak"]
                st.markdown(f"<span class='streak-pill'>🔥 {curr_s} days</span> &nbsp; <small>(Best: {best_s})</small>", unsafe_allow_html=True)

            with card_col4:
                st.write(f"Total: **{streak_info['total_completions']}** ✓")

            st.divider()

    # -------------------------------------------------------------
    # TAB 2: Weekly Matrix View
    # -------------------------------------------------------------
    with tab_weekly:
        st.subheader("🗓️ Current Week Consistency Matrix")
        st.caption("Check or uncheck any day of this week to update your logs.")

        # Determine Monday to Sunday of the current week
        today = date.today()
        start_of_week = today - timedelta(days=today.weekday())
        week_dates = [start_of_week + timedelta(days=i) for i in range(7)]

        header_cols = st.columns([0.3] + [0.1] * 7)
        header_cols[0].markdown("**Habit**")
        for i, d in enumerate(week_dates):
            is_cur = " •" if d == today else ""
            header_cols[i + 1].markdown(f"**{d.strftime('%a')}{is_cur}**<br><small>{d.strftime('%b %d')}</small>", unsafe_allow_html=True)

        for habit in habits:
            h_id = habit["id"]
            h_dates = get_all_completion_dates_for_habit(h_id)
            row_cols = st.columns([0.3] + [0.1] * 7)
            row_cols[0].markdown(f"{habit['icon']} **{habit['name']}**")

            for i, d in enumerate(week_dates):
                done = (d in h_dates)
                with row_cols[i + 1]:
                    if st.checkbox(
                        f"{d}",
                        value=done,
                        key=f"week_{h_id}_{d}",
                        label_visibility="collapsed"
                    ):
                        if not done:
                            toggle_habit_completion(h_id, d)
                            st.rerun()
                    else:
                        if done:
                            toggle_habit_completion(h_id, d)
                            st.rerun()

    # -------------------------------------------------------------
    # TAB 3: Progress & Analytics
    # -------------------------------------------------------------
    with tab_analytics:
        st.subheader("📊 Habit Streaks & Leaderboard")

        # Sorted by Current Streak descending
        ranked_habits = sorted(
            habits,
            key=lambda h: (calculate_streaks(h["id"])["current_streak"], calculate_streaks(h["id"])["total_completions"]),
            reverse=True
        )

        for rank, h in enumerate(ranked_habits, 1):
            s = calculate_streaks(h["id"])
            col_rank, col_name, col_curr, col_best, col_tot = st.columns([0.08, 0.42, 0.2, 0.15, 0.15])
            with col_rank:
                medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"#{rank}"
                st.write(f"### {medal}")
            with col_name:
                st.markdown(f"**{h['icon']} {h['name']}**")
                st.caption(f"Category: {h['category']}")
            with col_curr:
                st.metric("Current Streak", f"🔥 {s['current_streak']} days")
            with col_best:
                st.metric("Best Streak", f"🏆 {s['longest_streak']} days")
            with col_tot:
                st.metric("Total Done", f"{s['total_completions']} times")
            st.divider()

        # 30-Day Activity History
        st.subheader("📈 Recent Activity (Past 30 Days)")
        daily_counts = get_daily_completion_counts(days=30)
        if daily_counts:
            chart_data = {item["date"]: item["count"] for item in daily_counts}
            st.bar_chart(chart_data)
        else:
            st.info("Check in on your habits today to start populating your 30-day activity chart!")

        # Category Breakdown
        st.subheader("🏷️ Habit Completions by Category")
        cat_data = get_completions_by_category()
        if cat_data:
            c_cols = st.columns(len(cat_data))
            for i, (cat, count) in enumerate(cat_data.items()):
                with c_cols[i % len(c_cols)]:
                    st.metric(f"📂 {cat}", f"{count} check-ins")

    # -------------------------------------------------------------
    # TAB 4: Manage Habits (Delete, Details)
    # -------------------------------------------------------------
    with tab_manage:
        st.subheader("⚙️ Manage Habits")
        st.caption("Review your habits or remove those you no longer want to track.")

        for h in habits:
            m_col1, m_col2, m_col3 = st.columns([0.6, 0.25, 0.15])
            with m_col1:
                st.write(f"### {h['icon']} {h['name']}")
                st.write(f"Category: **{h['category']}** | Created: `{h['created_at']}`")
                if h["description"]:
                    st.caption(f"Description: {h['description']}")

            with m_col2:
                s = calculate_streaks(h["id"])
                st.metric("Total Check-ins", s["total_completions"])

            with m_col3:
                st.write("")
                st.write("")
                if st.button("🗑️ Delete", key=f"del_{h['id']}", type="secondary"):
                    delete_habit(h["id"])
                    st.success(f"Deleted habit '{h['name']}'")
                    st.rerun()

            st.divider()


if __name__ == "__main__":
    main()
