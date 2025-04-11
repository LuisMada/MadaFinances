# app.py
import streamlit as st
from modules import dashboard_ui

def main():
    """Main application function."""
    st.title("Financial Tracker Dashboard")
    
    # Add a note about using the Telegram bot
    with st.sidebar:
        st.header("Expense Logging")
        st.info(
            "📱 **New!** Log expenses through our Telegram bot!\n\n"
            "Find **@YourBotUsername** on Telegram to:\n"
            "- Log expenses on the go\n"
            "- Check summaries\n"
            "- Manage budgets\n\n"
            "This dashboard will automatically update with your latest data."
        )
    
    # Render the dashboard directly (no tabs needed)
    dashboard_ui.render_dashboard()

if __name__ == "__main__":
    main()