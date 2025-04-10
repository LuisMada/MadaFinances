"""
Presenter module for the financial tracker.
This module handles the communication between UI and business logic.
"""
from modules import openai_service, category_service, expense_service
from modules import expense_summary_service, budget_service

class FinancialPresenter:
    """
    Presenter class that coordinates between UI and business logic.
    This class handles the processing of user inputs and prepares data for UI display.
    """
    
    def process_user_input(self, user_input):
        """
        Process user input and determine appropriate response.
        
        Args:
            user_input (str): Natural language input from user
            
        Returns:
            str: Response to display to the user
        """
        # Check for summary intent first
        is_summary_request = openai_service.detect_summary_request(user_input)
        
        # Check for budget intent
        is_budget_request = openai_service.detect_budget_command(user_input)
        
        if is_summary_request:
            return self.handle_expense_summary(user_input)
        elif is_budget_request:
            # Extract budget details
            try:
                budget_data = openai_service.extract_budget_details(user_input)
                
                # Check if this is setting a budget or checking status
                if "set" in user_input.lower() or "create" in user_input.lower():
                    return self.handle_set_budget(budget_data)
                else:
                    return self.handle_budget_status({"period": "This Month"})  # Default to current month
            except Exception as e:
                return f"Error processing budget request: {str(e)}"
        else:
            # For non-budget, non-summary requests, use regular intent detection
            intent_data = openai_service.detect_intent(user_input)
            intent = intent_data.get("intent", "other")
            data = intent_data.get("data", {})
            
            # Process based on intent
            if intent == "expense":
                return self.handle_expense(user_input)
            elif intent == "summary":
                return self.handle_expense_summary(user_input)
            elif intent == "add_category":
                return self.handle_add_category(data)
            elif intent == "rename_category":
                return self.handle_rename_category(data)
            elif intent == "delete_category":
                return self.handle_delete_category(data)
            elif intent == "list_categories":
                return self.handle_list_categories()
            elif intent == "set_budget":
                return self.handle_set_budget(data)
            elif intent == "budget_status":
                return self.handle_budget_status(data)
            elif intent == "help":
                return self.handle_help()
            else:
                return "I'm not sure what you're asking. Try asking for help if you need guidance."
    
    def handle_add_category(self, data):
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
    
    def handle_rename_category(self, data):
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
    
    def handle_delete_category(self, data):
        """Handle deleting a category."""
        name = data.get("name", "").strip()
        
        if not name:
            return "Please provide a name for the category to delete."
        
        try:
            category_service.delete_category(name)
            return f"✅ Deleted category: {name}"
        except Exception as e:
            return f"Error deleting category: {str(e)}"
    
    def handle_list_categories(self):
        """Handle listing all categories."""
        try:
            # Get categories (this will use cache when available)
            categories = category_service.get_categories()
            
            if not categories:
                return "No categories found."
            
            categories_list = "\n".join([f"• {category}" for category in categories])
            return f"📋 Available categories:\n{categories_list}"
        except Exception as e:
            # Handle rate limit errors gracefully
            if "RESOURCE_EXHAUSTED" in str(e) or "Quota exceeded" in str(e):
                return "⚠️ Google Sheets API rate limit reached. Please try again in a minute."
            return f"Error listing categories: {str(e)}"
    
    def handle_expense(self, user_input):
        """Handle logging an expense."""
        try:
            return expense_service.handle_multiple_expenses(user_input)
        except Exception as e:
            return f"An error occurred: {str(e)}"
    
    def handle_expense_summary(self, user_input):
        """Handle request for expense summary."""
        try:
            # Use the formatted response directly from the service
            _, response, _ = expense_summary_service.handle_expense_summary(user_input)
            return response
        except Exception as e:
            return f"Error generating expense summary: {str(e)}"
    
    def handle_set_budget(self, data):
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
    
    def handle_budget_status(self, data):
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
    
    def handle_help(self):
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
    
    def initialize_categories(self):
        """Initialize categories and handle any errors."""
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
                except Exception as e:
                    if "already exists" not in str(e):
                        raise e
            
            return True, ""
        except Exception as e:
            error_msg = str(e)
            is_rate_limit = "RESOURCE_EXHAUSTED" in error_msg or "Quota exceeded" in error_msg
            
            if is_rate_limit:
                return False, "⚠️ Google Sheets API rate limit reached. Using cached categories. You can continue using the app."
            else:
                return False, f"Error setting up categories: {error_msg}"
    
    def get_dashboard_data(self, start_date, end_date, week_start_index=0):
        """
        Get all necessary data for dashboard display.
        
        Args:
            start_date: Start date for dashboard data
            end_date: End date for dashboard data
            week_start_index: Index of week start day (0=Monday)
            
        Returns:
            dict: Dictionary containing all dashboard data
        """
        # Get expenses
        expense_df = expense_summary_service.get_expenses_in_period(start_date, end_date)
        
        # Generate summary
        summary = expense_summary_service.generate_summary(expense_df)
        
        # Get budget status
        budget_status = budget_service.get_budget_status(start_date, end_date, week_start_index)
        
        return {
            "expense_df": expense_df,
            "summary": summary,
            "budget_status": budget_status
        }

# Create a singleton instance
presenter = FinancialPresenter()