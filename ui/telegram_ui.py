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
    
    def get_debt_keyboard(self):
        """
        Get a keyboard with debt-related options.
        
        Returns:
            InlineKeyboardMarkup: Debt-specific keyboard
        """
        keyboard = [
            [
                InlineKeyboardButton("💰 Check All Balances", callback_data="all_balances")
            ],
            [
                InlineKeyboardButton("➕ Add New Debt", callback_data="add_debt"),
                InlineKeyboardButton("✅ Settle Debt", callback_data="settle_debt")
            ],
            [
                InlineKeyboardButton("◀️ Back to Main Menu", callback_data="main_menu")
            ]
        ]
        
        return InlineKeyboardMarkup(keyboard)
    
    def format_debt_confirmation(self, debt_data):
        """
        Format a debt confirmation message.
        
        Args:
            debt_data (dict): Debt data
            
        Returns:
            str: Formatted message
        """
        person = debt_data.get("person", "Unknown")
        amount = debt_data.get("amount", 0)
        description = debt_data.get("description", "")
        direction = debt_data.get("direction", "from")
        
        if direction == "from":  # They owe you
            message = f"✅ Recorded: {person} owes you {amount}"
        else:  # You owe them
            message = f"✅ Recorded: You owe {person} {amount}"
            
        if description:
            message += f" for {description}"
            
        # Add syntax examples for future use
        message += f"\n\nQuick tips for next time:"
        if direction == "from":  # They owe you
            message += f"\n• '{amount} {description} ({person})' means {person} owes you"
        else:  # You owe them
            message += f"\n• '{amount} {description} - {person}' means you owe {person}"
            
        message += f"\n\nUse /balance to view current balances."
        
        return message
    
    def format_settlement_confirmation(self, settlement_data):
        """
        Format a settlement confirmation message.
        
        Args:
            settlement_data (dict): Settlement data
            
        Returns:
            str: Formatted message
        """
        person = settlement_data.get("person", "Unknown")
        amount = settlement_data.get("amount", 0)
        is_you_paying = settlement_data.get("is_you_paying", False)
        
        message = f"✅ Debt settled with {person} for {amount}\n"
        
        # Add expense note if you were the one paying
        if is_you_paying:
            message += f"💸 Payment recorded as an expense\n"
        
        # This assumes settlement_data contains a 'new_balance' field
        # that was added by the DebtService
        if "new_balance" in settlement_data:
            balance = settlement_data["new_balance"]
            if balance == 0:
                message += f"\nYou and {person} are now all square! 🎉"
            elif balance > 0:
                message += f"\n{person} still owes you: {balance}"
            else:
                message += f"\nYou still owe {person}: {abs(balance)}"
        else:
            message += "\nUse /balance to check updated balances"
        
        return message
    
    def format_balance_summary(self, balances_data):
        """
        Format a balance summary message.
        
        Args:
            balances_data (dict): Balance data from DebtService
            
        Returns:
            str: Formatted message
        """
        balances = balances_data.get("balances", [])
        
        if not balances:
            return "You have no active debts! 🎉"
        
        # Group by direction
        they_owe_you = []
        you_owe_them = []
        
        for balance in balances:
            if balance.get("they_owe", False):
                they_owe_you.append(balance)
            elif balance.get("you_owe", False):
                you_owe_them.append(balance)
        
        # Sort by amount (highest first)
        they_owe_you.sort(key=lambda x: x.get("amount", 0), reverse=True)
        you_owe_them.sort(key=lambda x: x.get("amount", 0), reverse=True)
        
        # Build message
        message = "📊 *Current Balances*\n\n"
        
        # Add people who owe you
        if they_owe_you:
            message += "*People who owe you:*\n"
            for balance in they_owe_you:
                message += f"• {balance.get('person', 'Unknown')}: {balance.get('amount', 0)}\n"
            message += "\n"
        
        # Add people you owe
        if you_owe_them:
            message += "*People you owe:*\n"
            for balance in you_owe_them:
                message += f"• {balance.get('person', 'Unknown')}: {balance.get('amount', 0)}\n"
            message += "\n"
        
        # Add totals
        total_owed_to_you = balances_data.get("total_owed_to_you", 0)
        total_you_owe = balances_data.get("total_you_owe", 0)
        net_position = balances_data.get("net_position", 0)
        
        message += "*Summary:*\n"
        message += f"Total owed to you: {total_owed_to_you}\n"
        message += f"Total you owe: {total_you_owe}\n"
        message += f"Net position: {net_position} {'(positive)' if net_position >= 0 else '(negative)'}"
        
        return message
    
    def get_main_keyboard_with_debt(self):
        """
        Get the main menu keyboard with debt tracking options.
        
        Returns:
            InlineKeyboardMarkup: Main menu keyboard with debt options
        """
        keyboard = [
            [
                InlineKeyboardButton("📊 Today's Expenses", callback_data="todays_expenses"),
                InlineKeyboardButton("💰 Balances", callback_data="all_balances")
            ],
            [
                InlineKeyboardButton("➕ New Debt", callback_data="add_debt"),
                InlineKeyboardButton("❓ Help", callback_data="help")
            ]
        ]
        
        return InlineKeyboardMarkup(keyboard)
        
    def format_help_message_with_debt(self):
        """Format a help message including debt tracking functionality."""
        return (
            "🤖 *Financial Tracker Bot Help*\n\n"
            "*EXPENSE TRACKING*\n"
            "• Type expenses like `coffee 3.50`\n"
            "• Multiple expenses: `coffee 3.50, lunch 12`\n\n"
            
            "*BUDGETING*\n"
            "• Set budget: `set 300 budget monthly`\n"
            "• Custom period: `set 200 budget for 5 days`\n"
            "• Check status: `budget status`\n\n"
            
            "*DEBT TRACKING*\n"
            "• Record when someone owes you: `200 hotdog (john)`\n"
            "• Record when you owe someone: `200 lunch - mary`\n"
            "• Other ways to record debts:\n"
            "  - `john owes me 500 for lunch`\n"
            "  - `i owe sara 350`\n"
            "• Settle debt: `settle 300 with alex`\n"
            "• Check balance: `/balance` or `check balance with sara`\n\n"
            
            "*SUMMARIES*\n"
            "• This month: `summary this month`\n"
            "• Last week: `summary last week`\n"
            "• Today: `today's expenses`\n\n"
            
            "*CATEGORIES*\n"
            "• Specify with: `coffee 3.50 Food`\n"
            "• Available: Food, Transportation, Entertainment, \n"
            "  Housing, Utilities, Healthcare, Shopping, Education, Other"
        )

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
        
    def format_budget_status(self, data):
        """
        Format budget status message.
        
        Args:
            data (dict): Budget status data
            
        Returns:
            str: Formatted message
        """
        status = data.get("status", "unknown")
        percentage_used = data.get("percentage_used", 0)
        remaining = data.get("remaining", 0)
        budget_amount = data.get("budget_amount", 0)
        total_spent = data.get("total_spent", 0)
        days_remaining = data.get("days_remaining", 0)
        remaining_daily = data.get("remaining_daily", 0)
        category = data.get("category", "all")
        period = data.get("period", "custom")
        
        if period == "custom":
            period_text = f"{data.get('days_total', 30)}-day period"
        else:
            period_text = period
            
        # Build message based on status
        if status == "over_budget":
            emoji = "🔴"
            status_text = "Over Budget"
        elif status == "near_limit":
            emoji = "🟠"
            status_text = "Near Limit"
        else:  # under_budget
            emoji = "🟢"
            status_text = "Under Budget"
            
        message = f"{emoji} *Budget Status: {status_text}*\n\n"
        
        # Add category if not 'all'
        if category.lower() != "all":
            message += f"Category: {category}\n"
            
        message += f"Budget: {budget_amount:.2f} ({period_text})\n"
        message += f"Spent: {total_spent:.2f} ({percentage_used:.1f}%)\n"
        message += f"Remaining: {remaining:.2f}\n\n"
        
        message += f"Days left: {days_remaining}\n"
        
        # Only show daily allowance if there are days remaining
        if days_remaining > 0:
            message += f"Daily allowance: {remaining_daily:.2f}\n"
            
        return message
            
    def format_budget_confirmation(self, budget_data):
        """
        Format a regular budget confirmation message.
        
        Args:
            budget_data (dict): Budget data
            
        Returns:
            str: Formatted message
        """
        period = budget_data.get("period", "monthly")
        category = budget_data.get("category", "all")
        amount = budget_data.get("amount", 0)
        
        message = f"✅ Budget Set: {amount} for {period} period"
        
        # Add category if it's not 'all'
        if category.lower() != "all":
            message += f" ({category} category)"
            
        message += "\n\nUse 'budget status' to check your spending against the budget."
        
        return message