import streamlit as st
import pandas as pd
import datetime
import altair as alt

CSV_FILE = "step_data.csv"
TEAM_GOAL = 500_000

# Load data
def load_data():
    try:
        df = pd.read_csv(CSV_FILE)
        if df.empty or df.columns.size == 0:
            df = pd.DataFrame(columns=["name", "start_date", "end_date", "steps"])
        else:
            df['start_date'] = pd.to_datetime(df['start_date'], errors='coerce')
            df['end_date'] = pd.to_datetime(df['end_date'], errors='coerce')
            df = df.dropna(subset=['start_date', 'end_date'])
    except (FileNotFoundError, pd.errors.EmptyDataError):
        df = pd.DataFrame(columns=["name", "start_date", "end_date", "steps"])
    return df

# Save data
def save_data(df):
    df.to_csv(CSV_FILE, index=False)

# Check for overlapping entries
def date_ranges_overlap(start1, end1, start2, end2):
    return max(start1, start2) <= min(end1, end2)

# Expand ranges into individual dates
def explode_dates(row):
    return pd.date_range(row['start_date'], row['end_date'])

# Constants
ALLOWED_START_DATE = datetime.date(2025, 7, 1)
ALLOWED_END_DATE = datetime.date(2025, 7, 31)

# UI setup
st.set_page_config(page_title="Team Step Challenge", layout="centered")
st.title("🚶‍♂️ Team Step Challenge Tracker")
st.markdown("Submit your steps for any date range in **July 2025**.")

ACCESS_PIN = "1234"
pin = st.text_input("🔐 Enter 4-digit PIN:", type="password", max_chars=4)

if pin != ACCESS_PIN:
    st.error("Access denied. Please enter the correct PIN to continue.")
    st.stop()


df = load_data()
name = st.text_input("Enter your name to login or register:")

if name:
    name = name.strip()
    st.success(f"Welcome, {name}!")

    with st.form("step_entry_form"):
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start date", value=ALLOWED_START_DATE,
                                       min_value=ALLOWED_START_DATE, max_value=ALLOWED_END_DATE)
        with col2:
            end_date = st.date_input("End date", value=ALLOWED_START_DATE,
                                     min_value=ALLOWED_START_DATE, max_value=ALLOWED_END_DATE)
        steps = st.number_input("Enter total steps for this range:", min_value=0, step=100)
        submitted = st.form_submit_button("Submit Steps")

        if submitted:
            if start_date > end_date:
                st.error("🚫 Start date cannot be after end date.")
            else:
                user_df = df[df['name'].str.lower() == name.lower()]
                overlap_found = any(date_ranges_overlap(start_date, end_date, r['start_date'].date(), r['end_date'].date()) for _, r in user_df.iterrows())

                if overlap_found:
                    st.error("❗ Overlapping entry detected. Choose a non-overlapping date range.")
                else:
                    new_entry = pd.DataFrame([[
                        name,
                        pd.Timestamp(start_date),
                        pd.Timestamp(end_date),
                        steps
                    ]], columns=["name", "start_date", "end_date", "steps"])
                    df = pd.concat([df, new_entry], ignore_index=True)
                    save_data(df)
                    st.success("✅ Steps submitted successfully!")

    df = load_data()

    # Explode data
    exploded = []
    for _, row in df.iterrows():
        dates = explode_dates(row)
        for d in dates:
            exploded.append({
                'name': row['name'],
                'date': d,
                'steps': row['steps'] / len(dates)
            })

    if exploded:
        exploded_df = pd.DataFrame(exploded)
        exploded_df['week'] = exploded_df['date'].dt.isocalendar().week
        exploded_df['steps'] = exploded_df['steps'].round().astype(int)

        # 📆 Selectable week filter
        st.subheader("📊 Weekly Leaderboard")
        weeks_available = sorted(exploded_df['week'].unique())
        selected_week = st.selectbox("Choose a week to view leaderboard:", weeks_available)

        week_data = exploded_df[exploded_df['week'] == selected_week]
        week_leaderboard = week_data.groupby('name')['steps'].sum().reset_index().sort_values(by='steps', ascending=False)

        st.bar_chart(week_leaderboard.set_index('name'))

        if not week_leaderboard.empty:
            top_user = week_leaderboard.iloc[0]
            st.success(f"🥇 Week {selected_week} Winner: **{top_user['name']}** with **{int(top_user['steps'])}** steps!")

        # 🧾 User submission history
        st.subheader("🗂️ Your Step Entries")
        user_entries = df[df['name'].str.lower() == name.lower()].sort_values(by='start_date')
        st.dataframe(user_entries)

        # 🏆 Monthly Leaderboard
        st.subheader("🏆 Monthly Leaderboard (July 2025)")
        monthly_df = exploded_df.groupby('name')['steps'].sum().reset_index().sort_values(by='steps', ascending=False)
        st.bar_chart(monthly_df.set_index("name"))

        # 🎯 Progress Tracker
        total_steps = exploded_df['steps'].sum()
        st.metric("📈 Team Progress", f"{int(total_steps)} / {TEAM_GOAL} steps")

        # 🌡️ Daily Step Heatmap
        st.subheader("📅 Daily Steps Heatmap")
        daily_totals = exploded_df.groupby('date')['steps'].sum().reset_index()
        chart = alt.Chart(daily_totals).mark_bar().encode(
            x='date:T',
            y='steps:Q',
            tooltip=['date:T', 'steps:Q']
        ).properties(title='Daily Step Totals')
        st.altair_chart(chart, use_container_width=True)

        # 🎉 Final winner on July 31
        if datetime.date.today() == datetime.date(2025, 7, 31):
            winner = monthly_df.iloc[0]
            st.balloons()
            st.success(f"🎉 Congratulations {winner['name']}! You are the **Monthly Winner** with **{int(winner['steps'])}** steps!")

    else:
        st.info("No step data available yet.")

else:
    st.info("Please enter your name to begin.")
