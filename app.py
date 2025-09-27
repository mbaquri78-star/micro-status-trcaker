import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import openai
import json
import os

# OpenAI Setup (replace with your key; falls back to simulation if not set)
#openai.api_key = os.getenv('OPENAI_API_KEY') or 'your-openai-api-key-here'  # Set via environment variable or Replit Secrets for security
USE_REAL_AI ="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"
#openai.api_key != 'your-openai-api-key-here'

# AI Analysis Function
@st.cache_data(ttl=300)  # Cache for 5 minutes to avoid repeated API calls
def analyze_status(description):
    if USE_REAL_AI:
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a project management AI. Analyze the status update: categorize as 'blocker' or 'win'. Identify owner group (e.g., IT, Business, QA, Team). Estimate impact (e.g., '1-week delay', 'no impact', 'positive momentum'). Output ONLY valid JSON: {'category': '...', 'owner_group': '...', 'impact': '...'}"
                    },
                    {"role": "user", "content": description}
                ],
                max_tokens=100,
                temperature=0.3
            )
            result = json.loads(response.choices[0].message.content.strip())
            return result
        except Exception as e:
	    st.error(f"AI analysis error: {e}. Using simulation.")
            # Fall back to simulation
    # Simulation (keyword-based for demo)
    desc_lower = description.lower()
    if any(word in desc_lower for word in ['miss', 'delay', 'block', 'issue', 'problem', 'error']):
        category = 'blocker'
        owner = 'IT' if any(word in desc_lower for word in ['data', 'tech', 'system']) else 'Business'
        impact = '1-week delay' if 'week' in desc_lower else 'Minor delay'
    else:
        category = 'win'
        owner = 'Team'
        impact = 'Positive momentum'
    return {'category': category, 'owner_group': owner, 'impact': impact}
# Database Setup
@st.cache_resource
def get_db_connection():
    conn = sqlite3.connect('statuses.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS statuses
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  timestamp TEXT,
                  user TEXT,
                  description TEXT,
                  category TEXT,
                  owner_group TEXT,
                  impact TEXT,
                  resolved BOOLEAN DEFAULT 0)''')
    conn.commit()
    return conn
# Streamlit App
st.set_page_config(page_title="Micro-Status Tracker", page_icon="📊", layout="wide")
st.title("📊 Micro-Status Tracker")
st.markdown("Capture real-time project updates, AI-analyze for impact, and get leadership summaries. Focus on blockers & wins to boost accountability!")
conn = get_db_connection()
# Sidebar: Submit Micro-Status
st.sidebar.header("📝 Submit Micro-Status")
user = st.sidebar.text_input("Your Name/Role", placeholder="e.g., John - Developer")
description = st.sidebar.text_area("Status Update", placeholder="e.g., 'Missed decision meeting—pushed a week' or 'Finished sprint task early!'", height=100)
category_hint = st.sidebar.selectbox("Quick Tag (optional)", ["", "Blocker", "Win"])  # Pre-categorize if desired
if st.sidebar.button("🚀 Submit Update", type="primary"):
    if user and description:
        analysis = analyze_status(description)
        # Override category if user tagged it
        if category_hint:
            analysis['category'] = category_hint.lower()
        timestamp = datetime.now().isoformat()
        c = conn.cursor()
        c.execute(
            "INSERT INTO statuses (timestamp, user, description, category, owner_group, impact, resolved) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (timestamp, user, description, analysis['category'], analysis['owner_group'], analysis['impact'], False)
        )
        conn.commit()
       st.sidebar.success("✅ Update submitted! Check the dashboard.")
        st.rerun()  # Refresh to show latest
    else:
        st.sidebar.warning("Please enter your name and a description.")
# Optional: Mark as Resolved (for leadership)
if st.sidebar.checkbox("Admin Mode: Mark Items Resolved"):
    unresolved_df = pd.read_sql_query("SELECT id FROM statuses WHERE resolved=0", conn)
    resolved_ids = st.sidebar.multiselect("Select IDs to Resolve", options=unresolved_df['id'].tolist() if not unresolved_df.empty else [])
    if resolved_ids and st.sidebar.button("Mark Resolved"):
        c = conn.cursor()
        for rid in resolved_ids:
            c.execute("UPDATE statuses SET resolved=1 WHERE id=?", (rid,))
        conn.commit()
        st.sidebar.success("Updated!")
        st.rerun()
# Main Dashboard
st.header("🔍 Real-Time Project Insights")
col1, col2 = st.columns([2, 1])
with col1:
    st.subheader("Recent Micro-Statuses (Last 20)")
    df = pd.read_sql_query(
        "SELECT * FROM statuses WHERE resolved=0 ORDER BY timestamp DESC LIMIT 20", conn
    )
    if not df.empty:
        for _, row in df.iterrows():
            with st.expander(f"**{row['user']}** ({row['timestamp'][:16]}) - {row['category'].title()}: {row['description'][:50]}..."):
                st.write(f"**Full Description:** {row['description']}")
                st.write(f"**Category:** {row['category'].title()}")
                st.write(f"**Owner Group:** {row['owner_group']}")
                st.write(f"**AI Impact Assessment:** {row['impact']}")
                if st.button(f"Mark Resolved (ID: {row['id']})", key=f"resolve_{row['id']}"):
                    c = conn.cursor()
                    c.execute("UPDATE statuses SET resolved=1 WHERE id=?", (row['id'],))
                    conn.commit()
                    st.rerun()
   else:
        st.info("👋 No updates yet. Submit one from the sidebar!")
with col2:
    st.subheader("📈 Quick Stats")
    total_query = pd.read_sql_query("SELECT COUNT(*) as count FROM statuses", conn)
    total = total_query.iloc[0]['count'] if not total_query.empty else 0
    blockers_query = pd.read_sql_query("SELECT COUNT(*) as count FROM statuses WHERE category='blocker' AND resolved=0", conn)
    blockers = blockers_query.iloc[0]['count'] if not blockers_query.empty else 0
    wins_query = pd.read_sql_query("SELECT COUNT(*) as count FROM statuses WHERE category='win'", conn)
    wins = wins_query.iloc[0]['count'] if not wins_query.empty else 0
    delays_query = pd.read_sql_query("SELECT COUNT(*) as count FROM statuses WHERE impact LIKE '%delay%'", conn)
    delays = delays_query.iloc[0]['count'] if not delays_query.empty else 0
    
    st.metric("Total Updates", total)
    st.metric("Active Blockers", blockers)
    st.metric("Wins", wins)
    st.metric("Delays Flagged", delays)
# AI-Generated Summary
st.subheader("🤖 AI Leadership Summary")
df_all = pd.read_sql_query("SELECT * FROM statuses ORDER BY timestamp DESC", conn)
if not df_all.empty:
    # Simple AI-like summary (enhance with real LLM call if needed)
    blocker_owners = df_all[df_all['category'] == 'blocker']['owner_group'].value_counts().to_dict()
    max_owner = max(blocker_owners, key=blocker_owners.get) if blocker_owners else 'N/A'
    max_count = blocker_owners.get(max_owner, 0)
    win_mode = df_all[df_all['category'] == 'win']['owner_group'].mode().iloc[0] if not df_all[df_all['category'] == 'win'].empty else 'Team'
    blocker_groups = ', '.join([k for k, v in blocker_owners.items() if v > 0]) if blocker_owners else 'None'
    
    summary_text = f"""
    - **Overview:** {blockers} active blockers and {wins} wins captured. {delays} potential delays could stack up if unaddressed.
    - **By Owner:** Blockers heaviest in {max_owner} ({max_count} issues).
    - **Recommendation:** Prioritize {blocker_groups}. Early action prevents timeline slips—aim for 80% resolution weekly.
    - **Momentum:** Wins show progress in {win_mode}.
    """
    st.markdown(summary_text)
else:
    st.info("No data for summary yet—start submitting updates!")
# Footer
st.markdown("---")
st.caption("Built with Streamlit & OpenAI. For integrations (e.g., Jira/Slack), reply with details. Data stored locally—backup `statuses.db` as needed.")
# Close connection (Streamlit handles it, but good practice)
if 'conn' in locals():
    conn.close()
