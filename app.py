# app.py
import streamlit as st
import datetime
import os
from modules import openai_service, sheets_service, category_service, expense_service, expense_summary_service, budget_service
from modules import dashboard_ui

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

def handle_add_category(data):
    """Handle adding a new category."""
    name = data.get("name", "").strip()
    description = data.get("description", "").strip()
    
    if not name:
        return "Please provide a name for the new category."
    
    try:
        category_service.add_category(name, description)
        return f"✅ Added new category: {name}"
    except Exception as e:
        return f"Error adding category: {str(e)}"

def handle_rename_category(data):
    """Handle renaming a category."""
    old_name = data.get("old_name", "").strip()
    new_name = data.get("new_name", "").strip()
    
    if not old_name or not new_name:
        return "Please provide both the old and new category names."
    
    try:
        category_service.rename_category(old_name, new_name)
        return f"✅ Renamed category from '{old_name}' to '{new_name}'"
    except Exception as e:
        return f"Error renaming category: {str(e)}"

def handle_delete_category(data):
    """Handle deleting a category."""
    name = data.get("name", "").strip()
    
    if not name:
        return "Please provide a name for the category to delete."
    
    try:
        category_service.delete_category(name)
        return f"✅ Deleted category: {name}"
    except Exception as e:
        return f"Error deleting category: {str(e)}"

def handle_list_categories():
    """Handle listing all categories."""
    try:
        # Get categories (this will use cache when available)
        categories = category_service.get_categories()
        print(f"Categories in handler: {categories}")
        
        if not categories:
            return "No categories found."
        
        categories_list = "\n".join([f"• {category}" for category in categories])
        return f"📋 Available categories:\n{categories_list}"
    except Exception as e:
        print(f"Error in handle_list_categories: {str(e)}")
        # Handle rate limit errors gracefully
        if "RESOURCE_EXHAUSTED" in str(e) or "Quota exceeded" in str(e):
            return "⚠️ Google Sheets API rate limit reached. Please try again in a minute."
        return f"Error listing categories: {str(e)}"
    
def handle_expense(user_input):
    """Handle logging an expense."""
    try:
        return expense_service.handle_multiple_expenses(user_input)
    except Exception as e:
        return f"An error occurred: {str(e)}"

def handle_expense_summary(user_input):
    """Handle request for expense summary."""
    try:
        # Use the formatted response directly from the service
        _, response, _ = expense_summary_service.handle_expense_summary(user_input)
        return response
    except Exception as e:
        return f"Error generating expense summary: {str(e)}"

def handle_help():
    """Handle help request."""
    help_text = """
    Here's what you can do:
    
    📝 **Log expenses** - Just tell me what you spent money on in natural language
    Example: "Spent ₱1225 on lunch yesterday"
    
    📊 **Get summaries** - Ask for expense summaries for different time periods
    Example: "Show my expenses this week" or "How much did I spend last month?"
    
    ➕ **Add a category** - Create a new expense category
    Example: "Add category Travel" or "Create new category Home with description Housing expenses"
    
    ✏️ **Rename a category** - Change a category name
    Example: "Rename category Food to Dining"
    
    🗑️ **Delete a category** - Remove a category you don't need
    Example: "Delete category Entertainment"
    
    📋 **List categories** - See all available categories
    Example: "Show all categories" or "List categories"
    
    📈 **View dashboard** - Switch to the Dashboard tab for visual expense summaries
    """
    return help_text

def handle_user_input(user_input):
    """Process user input and generate appropriate response."""
    # Add user message to chat
    add_message("user", user_input)
    
    # Use st.spinner to show a loading indicator while processing
    with st.spinner("Processing your request..."):
        # Check for summary intent first
        is_summary_request = openai_service.detect_summary_request(user_input)
        
        if is_summary_request:
            response = handle_expense_summary(user_input)
        else:
            # For non-summary requests, use regular intent detection
            intent_data = openai_service.detect_intent(user_input)
            intent = intent_data.get("intent", "other")
            data = intent_data.get("data", {})
            
            # Process based on intent
            if intent == "expense":
                response = handle_expense(user_input)
            elif intent == "summary":
                response = handle_expense_summary(user_input)
            elif intent == "add_category":
                response = handle_add_category(data)
            elif intent == "rename_category":
                response = handle_rename_category(data)
            elif intent == "delete_category":
                response = handle_delete_category(data)
            elif intent == "list_categories":
                response = handle_list_categories()
            elif intent == "help":
                response = handle_help()
            else:
                response = "I'm not sure what you're asking. Try asking for help if you need guidance."
        
        # Add assistant response
        add_message("assistant", response)
    
    # Force a rerun to update the UI
    st.experimental_rerun()

def handle_set_budget(data):
    """Handle setting a new budget."""
    amount = data.get("amount", 0)
    period = data.get("period", "monthly")
    category = data.get("category", "Total")
    
    if amount <= 0:
        return "Please provide a valid budget amount."
    
    try:
        # Set the budget
        budget_service.set_budget(amount, period, category)
        
        # Format response with proper currency symbol
        period_display = "monthly" if period.lower() == "monthly" else "weekly"
        category_display = f"for {category}" if category != "Total" else ""
        
        return f"✅ Set {period_display} budget of ₱{amount:.2f} {category_display}"
    except Exception as e:
        return f"Error setting budget: {str(e)}"

def handle_budget_status(data):
    """Handle request for budget status."""
    try:
        # Parse time period if provided
        period = data.get("period", "This Month")
        
        # Convert period to date range
        period_data = expense_summary_service.parse_time_period(period)
        start_date = period_data["start_date"]
        end_date = period_data["end_date"]
        
        # Get budget status
        budget_status = budget_service.get_budget_status(start_date, end_date)
        
        # Format the response
        response = budget_service.format_budget_status_response(budget_status)
        return response
    except Exception as e:
        return f"Error checking budget status: {str(e)}"

def handle_help():
    """Handle help request."""
    help_text = """
    Here's what you can do:
    
    📝 **Log expenses** - Just tell me what you spent money on in natural language
    Example: "Spent ₱1225 on lunch yesterday"
    
    📊 **Get summaries** - Ask for expense summaries for different time periods
    Example: "Show my expenses this week" or "How much did I spend last month?"
    
    💰 **Budget management** - Set and check budgets
    Example: "Set ₱5000 monthly budget" or "Set ₱1000 weekly food budget"
    
    📈 **Budget status** - Check how you're doing against your budget
    Example: "How's my budget?" or "Budget status for this month"
    
    ➕ **Add a category** - Create a new expense category
    Example: "Add category Travel" or "Create new category Home with description Housing expenses"
    
    ✏️ **Rename a category** - Change a category name
    Example: "Rename category Food to Dining"
    
    🗑️ **Delete a category** - Remove a category you don't need
    Example: "Delete category Entertainment"
    
    📋 **List categories** - See all available categories
    Example: "Show all categories" or "List categories"
    
    📈 **View dashboard** - Switch to the Dashboard tab for visual expense summaries
    """
    return help_text

# Update the handle_user_input function to include budget intents
def handle_user_input(user_input):
    """Process user input and generate appropriate response."""
    # Add user message to chat
    add_message("user", user_input)
    
    # Use st.spinner to show a loading indicator while processing
    with st.spinner("Processing your request..."):
        # Check for summary intent first
        is_summary_request = openai_service.detect_summary_request(user_input)
        
        # Check for budget intent
        is_budget_request = openai_service.detect_budget_command(user_input)
        
        if is_summary_request:
            response = handle_expense_summary(user_input)
        elif is_budget_request:
            # Extract budget details
            try:
                budget_data = openai_service.extract_budget_details(user_input)
                
                # Check if this is setting a budget or checking status
                if "set" in user_input.lower() or "create" in user_input.lower():
                    response = handle_set_budget(budget_data)
                else:
                    response = handle_budget_status({"period": "This Month"})  # Default to current month
            except Exception as e:
                response = f"Error processing budget request: {str(e)}"
        else:
            # For non-budget, non-summary requests, use regular intent detection
            intent_data = openai_service.detect_intent(user_input)
            intent = intent_data.get("intent", "other")
            data = intent_data.get("data", {})
            
            # Process based on intent
            if intent == "expense":
                response = handle_expense(user_input)
            elif intent == "summary":
                response = handle_expense_summary(user_input)
            elif intent == "add_category":
                response = handle_add_category(data)
            elif intent == "rename_category":
                response = handle_rename_category(data)
            elif intent == "delete_category":
                response = handle_delete_category(data)
            elif intent == "list_categories":
                response = handle_list_categories()
            elif intent == "set_budget":
                response = handle_set_budget(data)
            elif intent == "budget_status":
                response = handle_budget_status(data)
            elif intent == "help":
                response = handle_help()
            else:
                response = "I'm not sure what you're asking. Try asking for help if you need guidance."
        
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
        
        # Ensure categories sheet exists - with rate limit handling
        try:
            # Initialize categories (this will use cache if available)
            category_service.ensure_categories_sheet()
            
            # Initialize budget sheet
            budget_service.ensure_budgets_sheet()
            
            # Get categories from cache
            categories = category_service.get_categories()
            
            # Ensure Transportation category exists (no API call if already in cache)
            if "Transportation" not in categories:
                try:
                    category_service.add_category("Transportation", "Expenses for rides, taxis, public transit")
                    print("Added Transportation category")
                except Exception as e:
                    if "already exists" in str(e):
                        print("Transportation category already exists")
                    else:
                        print(f"Error adding Transportation category: {e}")
        except Exception as e:
            print(f"Error in category setup: {str(e)}")
            if "RESOURCE_EXHAUSTED" in str(e) or "Quota exceeded" in str(e):
                st.warning("⚠️ Google Sheets API rate limit reached. Using cached categories. You can continue using the app.")
            else:
                st.error(f"Error setting up categories: {str(e)}")
        
        # Display chat messages
        display_chat_messages()
        
        # Get user input
        if prompt := st.chat_input("Enter your expense or command..."):
            handle_user_input(prompt)
    
    with tab2:
        # Render the dashboard
        dashboard_ui.render_dashboard()

def main():
    """Main application function."""
    st.title("Financial Tracker")
    
    # Create tabs for chat and dashboard
    tab1, tab2 = st.tabs(["Chat", "Dashboard"])
    
    with tab1:
        # Initialize session state
        initialize_session_state()
        
        # Ensure categories sheet exists - with rate limit handling
        try:
            # Initialize categories (this will use cache if available)
            category_service.ensure_categories_sheet()
            
            # Get categories from cache
            categories = category_service.get_categories()
            
            # Ensure Transportation category exists (no API call if already in cache)
            if "Transportation" not in categories:
                try:
                    category_service.add_category("Transportation", "Expenses for rides, taxis, public transit")
                    print("Added Transportation category")
                except Exception as e:
                    if "already exists" in str(e):
                        print("Transportation category already exists")
                    else:
                        print(f"Error adding Transportation category: {e}")
        except Exception as e:
            print(f"Error in category setup: {str(e)}")
            if "RESOURCE_EXHAUSTED" in str(e) or "Quota exceeded" in str(e):
                st.warning("⚠️ Google Sheets API rate limit reached. Using cached categories. You can continue using the app.")
            else:
                st.error(f"Error setting up categories: {str(e)}")
        
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