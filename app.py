# app.py
import streamlit as st
import datetime
import os
from modules import category_service, budget_service
from modules import dashboard_ui
from modules.presenter import presenter

def initialize_session_state():
    """Initialize session state variables if they don't exist."""
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Hi! I'm your financial tracking assistant. Tell me about your expenses in natural language (e.g., 'Spent 200 on groceries'), ask for summaries (e.g., 'Show my expenses this week'), or manage your categories (e.g., 'Add category Travel')."}
        ]

def display_chat_messages():
    """Display all messages in the chat interface."""
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

def add_message(role, content):
    """Add a message to the chat history."""
    st.session_state.messages.append({"role": role, "content": content})

def handle_user_input(user_input):
    """Process user input and generate appropriate response using the presenter."""
    # Add user message to chat
    add_message("user", user_input)
    
    # Use st.spinner to show a loading indicator while processing
    with st.spinner("Processing your request..."):
        # Use the presenter to process the input
        response = presenter.process_user_input(user_input)
        
        # Add assistant response
        add_message("assistant", response)
    
    # Force a rerun to update the UI
    st.experimental_rerun()

def main():
    """Main application function."""
    st.title("Financial Tracker")
    
    # Create tabs for chat and dashboard
    tab1, tab2 = st.tabs(["Chat", "Dashboard"])
    
    with tab1:
        # Initialize session state
        initialize_session_state()
        
        # Initialize categories and handle any errors
        success, error_msg = presenter.initialize_categories()
        if not success and error_msg:
            if "rate limit" in error_msg.lower():
                st.warning(error_msg)
            else:
                st.error(error_msg)
        
        # Display chat messages
        display_chat_messages()
        
        # Get user input
        if prompt := st.chat_input("Enter your expense or command..."):
            handle_user_input(prompt)
    
    with tab2:
        # Render the dashboard
        dashboard_ui.render_dashboard()

if __name__ == "__main__":
    main()