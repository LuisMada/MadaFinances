"""
Dashboard UI for expense summaries and budget tracking in the financial tracker.
This module handles rendering expense summaries and budget status in the dashboard.
Separates UI presentation logic from business logic.
"""
import streamlit as st
import altair as alt
import pandas as pd
import datetime
from modules import expense_summary_service
from modules.presenter import presenter

# Define constants for weekday indices
MONDAY = 0
TUESDAY = 1
WEDNESDAY = 2
THURSDAY = 3
FRIDAY = 4
SATURDAY = 5
SUNDAY = 6

# Map weekday names to their numeric indices
WEEKDAY_MAP = {
    "Monday": MONDAY,
    "Tuesday": TUESDAY,
    "Wednesday": WEDNESDAY,
    "Thursday": THURSDAY,
    "Friday": FRIDAY,
    "Saturday": SATURDAY,
    "Sunday": SUNDAY
}

def render_sidebar_filters():
    """Render the sidebar filters and return selected values."""
    st.sidebar.header("Settings & Filters")
    
    # Week start day configuration
    week_start_day = st.sidebar.selectbox(
        "Week starts on",
        options=list(WEEKDAY_MAP.keys()),
        index=3  # Default to Monday
    )
    # Store the selected day's index for calculations
    week_start_index = WEEKDAY_MAP[week_start_day]
    
    # Save the setting in session state so it persists between reruns
    if "week_start_index" not in st.session_state:
        st.session_state.week_start_index = week_start_index
    else:
        st.session_state.week_start_index = week_start_index
    
    # Add time period filter in sidebar
    st.sidebar.subheader("Time Period")
    time_period = st.sidebar.selectbox(
        "Select time period",
        options=["Today", "This Week", "This Month", "Last Month", "This Year", "Custom"]
    )
    
    # Initialize start and end dates
    today = datetime.date.today()
    start_date = today
    end_date = today
    
    # Set date range based on selection
    if time_period == "Custom":
        date_range = st.sidebar.date_input(
            "Select date range",
            value=(today.replace(day=1), today),
            max_value=today
        )
        
        if len(date_range) == 2:
            start_date, end_date = date_range
        else:
            start_date = end_date = today
    else:
        # Use the preselected time period
        period_data = expense_summary_service.parse_time_period(time_period)
        start_date = period_data["start_date"]
        end_date = period_data["end_date"]
        
        st.sidebar.write(f"From: {start_date.strftime('%b %d, %Y')}")
        st.sidebar.write(f"To: {end_date.strftime('%b %d, %Y')}")
    
    return {
        "start_date": start_date,
        "end_date": end_date,
        "time_period": time_period,
        "week_start_index": week_start_index
    }

def render_summary_cards(summary, budget_status):
    """Render summary statistics in cards."""
    st.subheader("Summary")
    
    if not summary["data_available"]:
        st.info("No expenses found for this period.")
        return
        
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            label="Total Expenses",
            value=f"₱{summary['total_expenses']:.2f}"
        )

    with col2:
        st.metric(
            label="Number of Transactions",
            value=summary['num_transactions']
        )

    with col3:
        # Replace average expense with a placeholder for total savings
        # We'll update this after getting the budget status
        if budget_status.get("has_budget", False):
            total_savings = budget_status["total_budget"] - summary['total_expenses']
            savings_color = "normal" if total_savings >= 0 else "inverse"
            savings_label = "surplus" if total_savings >= 0 else "deficit"
            
            st.metric(
                label="Total Savings", 
                value=f"₱{abs(total_savings):.2f} {savings_label}",
                delta=f"{abs(total_savings / budget_status['total_budget'] * 100):.1f}% of budget",
                delta_color=savings_color
            )
        else:
            st.metric(
                label="Total Savings", 
                value="No budget set"
            )

def render_budget_status(budget_status, week_start_index):
    """Render budget status section."""
    if budget_status.get("has_budget", False):
        st.subheader("Budget Status")
        
        # Budget summary metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Show progress against weekly budget
            st.metric(
                label="Weekly Budget",  # Updated label
                value=f"₱{budget_status['remaining']:.2f} left",
                delta=f"₱{budget_status['total_budget']:.2f}"
            )
            
            # Budget progress bar
            percent_used = min(100, budget_status["percent_used"])
            
            # Choose color based on status
            bar_color = "normal"
            if budget_status["status"] == "over_budget":
                bar_color = "off"
            elif budget_status["status"] == "near_limit":
                bar_color = "warning"
                
            st.progress(percent_used / 100, text=f"{percent_used:.1f}% Used")
            
        with col2:
            # Daily average metrics
            st.metric(
                label="Daily Budget",
                value=f"₱{budget_status['daily_budget']:.2f}",
                delta=f"₱{budget_status['daily_average']:.2f} spent on average",
                delta_color="inverse"
            )
            
        with col3:
            # Show remaining daily allowance
            if budget_status["days_remaining"] > 0:
                st.metric(
                    label="Daily Allowance",
                    value=f"₱{budget_status['remaining_daily_allowance']:.2f}",
                    delta=f"{budget_status['days_remaining']} days left"
                )
            else:
                st.metric(
                    label="Period Status",
                    value="Completed",
                    delta=f"₱{budget_status['remaining']:.2f} {'surplus' if budget_status['remaining'] >= 0 else 'deficit'}"
                )
    else:
        st.subheader("Budget Status")
        st.info("No budget set for this period. Set a budget with a command like 'Set ₱1000 monthly budget'.")

def render_weekly_comparison(df, budget_status, start_date, week_start_index):
    """Render weekly expenses comparison section."""
    if not df.empty and budget_status.get("has_budget", False):
        # Calculate weekly budget metrics
        weekly_budget = budget_status.get('weekly_budget', budget_status['daily_budget'] * 7)
        
        # Calculate the week number relative to start date
        def get_week_of_date(date, start_date, week_start_index):
            """
            Calculate the week number, respecting the configured start day of week.
            
            Args:
                date: The date to get the week number for
                start_date: The reference start date
                week_start_index: Index of the day that starts the week (0=Monday, 6=Sunday)
            """
            # Calculate the nearest week start day before or equal to start_date
            start_weekday = start_date.weekday()
            days_to_subtract = (start_weekday - week_start_index) % 7
            week_start = start_date - datetime.timedelta(days=days_to_subtract)
            
            # Calculate days since that week start
            days_diff = (date - week_start).days
            
            # Calculate week number (1-based)
            return (days_diff // 7) + 1
        
        # Get current week data
        today = datetime.date.today()
        current_week_num = get_week_of_date(today, start_date, week_start_index)
        
        # Calculate expenses by week, using the configured start day
        df_with_week = df.copy()
        df_with_week['Week'] = df_with_week['Date'].apply(
            lambda x: get_week_of_date(x.date(), start_date, week_start_index)
        )
        weekly_expenses = df_with_week.groupby('Week')['Amount'].sum().to_dict()
        
        # Get current and previous week expenses
        current_week_expenses = weekly_expenses.get(current_week_num, 0)
        prev_week_expenses = weekly_expenses.get(current_week_num - 1, 0) if current_week_num > 1 else 0
        
        # Calculate average weekly expenses
        total_weeks = max(weekly_expenses.keys()) if weekly_expenses else 0
        avg_weekly_expenses = sum(weekly_expenses.values()) / max(1, len(weekly_expenses))
        
        # Weekly Expenses Comparison
        st.subheader("Weekly Expenses Comparison")

        # Create columns for weekly comparison metrics
        col1, col2, col3 = st.columns(3)

        with col1:
            # This week vs budget
            week_budget_diff = current_week_expenses - weekly_budget
            
            if current_week_num <= total_weeks:
                st.metric(
                    label=f"Week {current_week_num} Expenses",
                    value=f"₱{current_week_expenses:.2f}",
                    delta=f"₱{abs(week_budget_diff):.2f} {'over' if week_budget_diff > 0 else 'under'} budget",
                    delta_color="inverse" if week_budget_diff > 0 else "normal"
                )
            else:
                st.metric(
                    label="Weekly Budget",
                    value=f"₱{weekly_budget:.2f}"
                )

        with col2:
            # Previous week's savings/surplus instead of just expenses
            if current_week_num > 1 and prev_week_expenses > 0:
                # Calculate savings from previous week (budget - expenses)
                prev_week_savings = weekly_budget - prev_week_expenses
                
                # Use a positive message for savings, negative for overspending
                if prev_week_savings >= 0:
                    savings_label = "Previous Week Spendings"
                    savings_message = f"₱{prev_week_savings:.2f} saved"
                    savings_color = "normal"
                else:
                    savings_label = "Previous Week Overspent"
                    savings_message = f"₱{abs(prev_week_savings):.2f} over budget"
                    savings_color = "inverse"
                
                st.metric(
                    label=savings_label,
                    value=f"₱{prev_week_expenses:.2f}",
                    delta=savings_message,
                    delta_color=savings_color
                )
            else:
                st.metric(
                    label="Previous Week Spending",
                    value="No data"
                )

        with col3:
            # Average weekly expenses
            if total_weeks > 0:
                avg_diff = avg_weekly_expenses - weekly_budget
                st.metric(
                    label="Avg Weekly Expenses",
                    value=f"₱{avg_weekly_expenses:.2f}",
                    delta=f"₱{abs(avg_diff):.2f} {'over' if avg_diff > 0 else 'under'} budget",
                    delta_color="inverse" if avg_diff > 0 else "normal"
                )
            else:
                st.metric(
                    label="Avg Weekly Expenses",
                    value="No data"
                )

def render_daily_comparison(df, budget_status, start_date, end_date, time_period, week_start_index):
    """Render daily expenses comparison section."""
    st.subheader("Daily Expenses Comparison")
    
    if not df.empty:
        # Calculate metrics for today's expenses if available
        today_date = datetime.date.today()
        if start_date <= today_date <= end_date:
            today_expenses = df[df['Date'].dt.date == today_date]['Amount'].sum()
            
            # Calculate yesterday's expenses if within range
            yesterday_date = today_date - datetime.timedelta(days=1)
            yesterday_expenses = 0
            if start_date <= yesterday_date <= end_date:
                yesterday_expenses = df[df['Date'].dt.date == yesterday_date]['Amount'].sum()
            
            # Create columns for daily comparison metrics
            col1, col2, col3 = st.columns(3)
            
            with col1:
                # Today's expenses vs daily budget
                budget_diff = today_expenses - budget_status['daily_budget']
                st.metric(
                    label="Today's Expenses",
                    value=f"₱{today_expenses:.2f}",
                    delta=f"₱{abs(budget_diff):.2f} {'over' if budget_diff > 0 else 'under'} budget",
                    delta_color="inverse" if budget_diff > 0 else "normal"
                )
            
            with col2:
                # Today vs yesterday
                if yesterday_date >= start_date:
                    day_diff = today_expenses - yesterday_expenses
                    st.metric(
                        label="vs. Yesterday",
                        value=f"₱{yesterday_expenses:.2f}",
                        delta=f"₱{abs(day_diff):.2f} {'more' if day_diff > 0 else 'less'} today",
                        delta_color="inverse" if day_diff > 0 else "normal"
                    )
                else:
                    st.metric(
                        label="Today vs. Daily Avg",
                        value=f"₱{today_expenses:.2f}",
                        delta=f"₱{abs(today_expenses - budget_status['daily_average']):.2f} {'more' if today_expenses > budget_status['daily_average'] else 'less'} than avg",
                        delta_color="inverse" if today_expenses > budget_status['daily_average'] else "normal"
                    )
            
            with col3:
                # Weekly average calculation
                if time_period.lower() in ["this week", "this month", "last month", "this year"]:
                    # Get current week's expenses - using the configured start day of week
                    today_weekday = today_date.weekday()
                    days_since_week_start = (today_weekday - week_start_index) % 7
                    week_start = today_date - datetime.timedelta(days=days_since_week_start)
                    week_end = min(week_start + datetime.timedelta(days=6), end_date)
                    
                    if week_start >= start_date:
                        week_expenses = df[(df['Date'].dt.date >= week_start) & (df['Date'].dt.date <= week_end)]['Amount'].sum()
                        days_in_week = min((today_date - week_start).days + 1, 7)
                        weekly_daily_avg = week_expenses / max(1, days_in_week)
                        
                        st.metric(
                            label="This Week Daily Avg",
                            value=f"₱{weekly_daily_avg:.2f}",
                            delta=f"₱{abs(weekly_daily_avg - budget_status['daily_budget']):.2f} {'over' if weekly_daily_avg > budget_status['daily_budget'] else 'under'} budget",
                            delta_color="inverse" if weekly_daily_avg > budget_status['daily_budget'] else "normal"
                        )
                    else:
                        # If not this week, show period average
                        st.metric(
                            label="Period Daily Avg",
                            value=f"₱{budget_status['daily_average']:.2f}",
                            delta=f"₱{abs(budget_status['daily_average'] - budget_status['daily_budget']):.2f} {'over' if budget_status['daily_average'] > budget_status['daily_budget'] else 'under'} budget",
                            delta_color="inverse" if budget_status['daily_average'] > budget_status['daily_budget'] else "normal"
                        )
                else:
                    # Show period average for other time periods
                    st.metric(
                        label="Period Daily Avg",
                        value=f"₱{budget_status['daily_average']:.2f}",
                        delta=f"₱{abs(budget_status['daily_average'] - budget_status['daily_budget']):.2f} {'over' if budget_status['daily_average'] > budget_status['daily_budget'] else 'under'} budget",
                        delta_color="inverse" if budget_status['daily_average'] > budget_status['daily_budget'] else "normal"
                    )
        else:
            # If today is not in the selected period, show a message
            st.info("Today's expenses are not available for the selected period.")
    else:
        st.info("No daily expense data available for the selected period.")

def render_category_budgets(budget_status):
    """Render category budget status section."""
    if budget_status.get("categories"):
        st.subheader("Category Budgets")
        
        # Prepare data for visualization
        category_data = []
        for category, data in budget_status["categories"].items():
            category_data.append({
                "Category": category,
                "Spent": data["spent"],
                "Budget": data["budget"],
                "PercentUsed": data["percent_used"],
                "Remaining": data["remaining"]
            })
        
        if category_data:
            category_df = pd.DataFrame(category_data)
            
            # Create category budget chart
            chart = alt.Chart(category_df).mark_bar().encode(
                x=alt.X("Spent:Q", title="Amount (₱)"),
                y=alt.Y("Category:N", sort="-x", title=None),
                color=alt.condition(
                    alt.datum.PercentUsed > 100,
                    alt.value("red"),
                    alt.condition(
                        alt.datum.PercentUsed > 85,
                        alt.value("orange"),
                        alt.value("green")
                    )
                ),
                tooltip=["Category", "Spent", "Budget", "Remaining", "PercentUsed"]
            ).properties(
                title="Spending by Category",
                height=30 * len(category_df)
            )
            
            # Add budget markers
            budget_markers = alt.Chart(category_df).mark_rule(color="black", strokeDash=[3, 3]).encode(
                x="Budget:Q",
                y="Category:N"
            )
            
            # Combine both layers
            combined_chart = alt.layer(chart, budget_markers)
            
            st.altair_chart(combined_chart, use_container_width=True)

def render_expense_breakdown(summary):
    """Render expense breakdown by category section."""
    st.subheader("Expense Breakdown by Category")
    
    # Prepare data for charts
    category_data = []
    for category, data in summary["by_category"].items():
        category_data.append({
            "Category": category,
            "Amount": data["amount"],
            "Percentage": data["percentage"]
        })
    
    category_df = pd.DataFrame(category_data)
    
    # Create two columns for charts
    col1, col2 = st.columns(2)
    
    with col1:
        # Category breakdown as pie chart
        if not category_df.empty:
            pie_chart = alt.Chart(category_df).mark_arc().encode(
                theta=alt.Theta(field="Amount", type="quantitative"),
                color=alt.Color(field="Category", type="nominal"),
                tooltip=["Category", "Amount", "Percentage"]
            ).properties(
                title="Expenses by Category",
                width=200,
                height=200
            )
            
            st.altair_chart(pie_chart, use_container_width=True)
    
    with col2:
        # Category breakdown as bar chart
        if not category_df.empty:
            sorted_df = category_df.sort_values("Amount", ascending=False)
            
            bar_chart = alt.Chart(sorted_df).mark_bar().encode(
                x=alt.X("Amount:Q", title="Amount (₱)"),
                y=alt.Y("Category:N", sort="-x", title=None),
                tooltip=["Category", "Amount", "Percentage"]
            ).properties(
                title="Top Categories",
                width=300
            )
            
            st.altair_chart(bar_chart, use_container_width=True)

def render_transaction_list(df):
    """Render transaction list section."""
    st.subheader("Recent Transactions")
    
    if not df.empty:
        # Format DataFrame for display
        display_df = df.copy()
        display_df["Date"] = display_df["Date"].dt.strftime("%b %d, %Y")
        display_df["Amount"] = display_df["Amount"].apply(lambda x: f"₱{x:.2f}")
        
        # Sort by date (latest first)
        display_df = display_df.sort_values("Date", ascending=False)
        
        # Show in table
        st.dataframe(
            display_df[["Date", "Category", "Description", "Amount"]],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No transactions to display.")

def render_dashboard():
    """Render the expense summary dashboard."""
    st.header("Expense Summary Dashboard")
    
    # Get filter values from sidebar
    filters = render_sidebar_filters()
    start_date = filters["start_date"]
    end_date = filters["end_date"]
    time_period = filters["time_period"]
    week_start_index = filters["week_start_index"]
    
    # Get data from presenter
    dashboard_data = presenter.get_dashboard_data(start_date, end_date, week_start_index)
    expense_df = dashboard_data["expense_df"]
    summary = dashboard_data["summary"]
    budget_status = dashboard_data["budget_status"]
    
    # Render dashboard sections
    render_summary_cards(summary, budget_status)
    
    if summary["data_available"]:
        render_budget_status(budget_status, week_start_index)
        render_weekly_comparison(expense_df, budget_status, start_date, week_start_index)
        render_daily_comparison(expense_df, budget_status, start_date, end_date, time_period, week_start_index)
        render_category_budgets(budget_status)
        render_expense_breakdown(summary)
        render_transaction_list(expense_df)