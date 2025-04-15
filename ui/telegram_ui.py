"""
Simplified Telegram UI Components
Contains only essential keyboard layouts and formatting functions.
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

class TelegramUI:
    def __init__(self):
        """Initialize UI components."""
        pass
    
    def get_main_keyboard(self):
        """
        Get the simplified main menu keyboard with only Today's Expenses and Help.
        
        Returns:
            InlineKeyboardMarkup: Main menu keyboard
        """
        keyboard = [
            [
                InlineKeyboardButton("📊 Today's Expenses", callback_data="todays_expenses")
            ],
            [
                InlineKeyboardButton("❓ Help", callback_data="help")
            ]
        ]
        
        return InlineKeyboardMarkup(keyboard)
    
    def format_todays_expenses(self, expenses, budget_data=None):
        """
        Format today's expenses with budget information.
        
        Args:
            expenses (list): List of expenses for today
            budget_data (dict, optional): Budget data
            
        Returns:
            str: Formatted message
        """
        if not expenses:
            return "No expenses recorded for today."
        
        # Calculate total spent today
        try:
            total_spent = sum(float(exp.get('Amount', 0)) for exp in expenses)
        except:
            # Handle case where Amount might not be a number
            total_spent = 0
            for exp in expenses:
                try:
                    amount = float(exp.get('Amount', 0))
                    total_spent += amount
                except:
                    pass
        
        # Start building the message
        message = "📋 **Today's Expenses**\n\n"
        
        # List all expenses
        for i, expense in enumerate(expenses, 1):
            try:
                description = expense.get('Description', 'Unknown')
                amount = expense.get('Amount', '0.00')
                category = expense.get('Category', 'Other')
                message += f"{i}. {description} - {amount} ({category})\n"
            except:
                # Skip expenses that cause formatting errors
                message += f"{i}. [Error formatting expense]\n"
        
        # Add total
        message += f"\n**Total spent today**: {total_spent:.2f}\n"
        
        # Add budget information if available
        if budget_data:
            try:
                budget_amount = float(budget_data.get('budget_amount', 0))
                remaining = float(budget_data.get('remaining', 0))
                days_remaining = int(budget_data.get('days_remaining', 0))
                
                message += f"\n**Budget Information**:\n"
                message += f"Budget: {budget_amount:.2f}\n"
                message += f"Remaining: {remaining:.2f}\n"
                message += f"Days left: {days_remaining}\n"
                
                # Add daily allowance if there are days remaining
                if days_remaining > 0:
                    daily_allowance = remaining / days_remaining
                    message += f"Daily allowance: {daily_allowance:.2f}\n"
            except Exception as e:
                # If there's an error formatting budget data, just show a simple message
                message += "\n**Budget Information**: Available but could not be displayed\n"
        else:
            message += "\n*No active budget found. Set a budget with 'set 300 budget for 14 days'*"
        
        return message
    
    def format_expense_confirmation(self, expense_data):
        """
        Format an expense confirmation message.
        
        Args:
            expense_data (dict): Expense data
            
        Returns:
            str: Formatted message
        """
        amount = expense_data.get("amount", 0)
        description = expense_data.get("description", "expense")
        category = expense_data.get("category", "Other")
        date = expense_data.get("date", "today")
        
        message = f"✅ Logged: {amount} for {description}\n"
        message += f"Category: {category}, Date: {date}"
        
        return message
    
    def format_help_message(self):
        """Format a help message with the bot's capabilities."""
        return (
            "🤖 *Financial Tracker Bot Help*\n\n"
            "*EXPENSE TRACKING*\n"
            "• Type expenses like `coffee 3.50`\n"
            "• Multiple expenses: `coffee 3.50, lunch 12`\n\n"
            
            "*SHARED EXPENSES*\n"
            "• Track when someone owes you:\n"
            "  `200 lunch (Jana)` → Jana owes you ₱200\n"
            "• Track when you owe someone:\n"
            "  `200 lunch - Jana` → You owe Jana ₱200\n"
            "• View debts:\n"
            "  `/utang` → people who owe you\n"
            "  `/owe` → people you owe\n"
            "• Settle a debt:\n"
            "  `settle Jana 40` → mark as paid\n\n"
            
            "*BUDGETING*\n"
            "• Set budget: `set 300 budget monthly`\n"
            "• Custom period: `set 200 budget for 5 days`\n"
            "• Check status: `budget status`\n\n"
            
            "*SUMMARIES*\n"
            "• This month: `summary this month`\n"
            "• Last week: `summary last week`\n"
            "• Today: `today's expenses`\n\n"
            
            "*CATEGORIES*\n"
            "• Specify with: `coffee 3.50 Food`\n"
            "• Available: Food, Transportation, Entertainment, \n"
            "  Housing, Utilities, Healthcare, Shopping, Education, Other"
        )
    
    """
    Add this method to your TelegramUI class in telegram_ui.py
    """

    def get_custom_period_keyboard(self):
        """
        Get the custom period selection keyboard.
        
        Returns:
            InlineKeyboardMarkup: Custom period keyboard
        """
        keyboard = [
            [
                InlineKeyboardButton("3 Days", callback_data="set_custom_budget_3"),
                InlineKeyboardButton("7 Days", callback_data="set_custom_budget_7"),
                InlineKeyboardButton("14 Days", callback_data="set_custom_budget_14")
            ],
            [
                InlineKeyboardButton("30 Days", callback_data="set_custom_budget_30"),
                InlineKeyboardButton("90 Days", callback_data="set_custom_budget_90")
            ],
            [
                InlineKeyboardButton("Custom Number", callback_data="set_custom_budget_input"),
                InlineKeyboardButton("Back", callback_data="help")
            ]
        ]
        
        return InlineKeyboardMarkup(keyboard)

    def format_custom_period_confirmation(self, budget_data):
        """
        Format a custom period budget confirmation message.
        
        Args:
            budget_data (dict): Budget data
            
        Returns:
            str: Formatted message
        """
        days = budget_data.get("days", 30)
        category = budget_data.get("category", "all")
        amount = budget_data.get("amount", 0)
        
        message = f"✅ Custom Budget Set: {amount} for {days} days"
        
        # Add category if it's not 'all'
        if category.lower() != "all":
            message += f" ({category} category)"
        
        # Add start date if available
        if "start_date" in budget_data:
            message += f"\nStarting: {budget_data['start_date']}"
        
        message += "\n\nUse the 'Today's Expenses' button to check your current spending status."
        
        return message