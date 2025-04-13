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
        """
        Format the simplified help message.
        
        Returns:
            str: Formatted help message
        """
        help_text = (
            "🤖 **Financial Tracker Bot Help**\n\n"
            
            "📝 **Logging Expenses**\n"
            "• Type `coffee 3.50` to log an expense\n"
            "• You can include a category: `lunch 12 food`\n"
            "• Multiple expenses: `coffee 3.50, taxi 15`\n\n"
            
            "💰 **Budget Management**\n"
            "• Set a budget: `set 300 budget for 14 days`\n\n"
            
            "📊 **View Expenses**\n"
            "• Click 'Today's Expenses' button to see today's spending\n\n"
            
            "🗑️ **Deleting Expenses**\n"
            "• Type: `delete coffee` to remove coffee expenses\n"
        )
        
        return help_text