"""
Telegram UI Module
Handles UI components and formatting for the Telegram bot.
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import datetime

class TelegramUI:
    """Handles UI components and formatting for the Telegram bot."""
    
    def get_main_keyboard(self):
        """Return the main menu keyboard."""
        keyboard = [
            [
                InlineKeyboardButton("📊 Summary", callback_data="summary"),
                InlineKeyboardButton("💰 Budget", callback_data="budget")
            ],
            [
                InlineKeyboardButton("🗑️ Delete Expense", callback_data="delete_expense"),
                InlineKeyboardButton("❓ Help", callback_data="help")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def get_summary_keyboard(self):
        """Return the summary options keyboard."""
        keyboard = [
            [
                InlineKeyboardButton("Today", callback_data="summary_today"),
                InlineKeyboardButton("This Week", callback_data="summary_this_week"),
                InlineKeyboardButton("This Month", callback_data="summary_this_month")
            ],
            [
                InlineKeyboardButton("Last Week", callback_data="summary_last_week"),
                InlineKeyboardButton("Last Month", callback_data="summary_last_month")
            ],
            [
                InlineKeyboardButton("« Back to Main Menu", callback_data="main_menu")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def get_budget_keyboard(self):
        """Return the budget options keyboard."""
        keyboard = [
            [
                InlineKeyboardButton("Check Status", callback_data="budget_status")
            ],
            [
                InlineKeyboardButton("Set Weekly Budget", callback_data="set_weekly_budget"),
                InlineKeyboardButton("Set Monthly Budget", callback_data="set_monthly_budget")
            ],
            [
                InlineKeyboardButton("Set Custom Period Budget", callback_data="set_custom_budget")
            ],
            [
                InlineKeyboardButton("« Back to Main Menu", callback_data="main_menu")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def get_custom_period_keyboard(self):
        """Return the custom period selection keyboard."""
        keyboard = [
            [
                InlineKeyboardButton("3 Days", callback_data="set_custom_budget_3"),
                InlineKeyboardButton("5 Days", callback_data="set_custom_budget_5"),
                InlineKeyboardButton("7 Days", callback_data="set_custom_budget_7")
            ],
            [
                InlineKeyboardButton("10 Days", callback_data="set_custom_budget_10"),
                InlineKeyboardButton("14 Days", callback_data="set_custom_budget_14"),
                InlineKeyboardButton("21 Days", callback_data="set_custom_budget_21")
            ],
            [
                InlineKeyboardButton("Custom...", callback_data="set_custom_budget_custom"),
                InlineKeyboardButton("« Back", callback_data="budget")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def format_help_message(self):
        """Return a formatted help message."""
        return (
            "📱 *Financial Tracker Bot Help*\n\n"
            "*Track Expenses*\n"
            "Simply type an expense like:\n"
            "`coffee 3.50`\n"
            "`lunch 12.99 food`\n"
            "`taxi 15 transportation yesterday`\n\n"
            
            "*Multiple Expenses*\n"
            "You can log multiple expenses in one message:\n"
            "`coffee 3.50, lunch 12.99`\n\n"
            
            "*Budget Commands*\n"
            "Set a budget:\n"
            "`set monthly budget 1000`\n"
            "`set weekly food budget 200`\n"
            "`set budget 500 for next 14 days`\n\n"
            
            "*Check Status*\n"
            "`budget status`\n"
            "`how much left in budget`\n\n"
            
            "*Get Summaries*\n"
            "`summary for this week`\n"
            "`spending this month`\n"
            "`expenses yesterday`\n\n"
            
            "*Delete Expenses*\n"
            "`delete coffee expense`\n"
            "`remove taxi payment`"
        )
    
    def format_expense_confirmation(self, expense_data):
        """Format an expense confirmation message."""
        # Format the date
        try:
            date_obj = datetime.datetime.strptime(expense_data["date"], "%Y-%m-%d").date()
            formatted_date = date_obj.strftime("%b %d")
        except:
            formatted_date = expense_data["date"]
        
        # Create the confirmation message
        msg = f"✅ Logged expense: {expense_data['description']}\n"
        msg += f"💲 Amount: {expense_data['amount']}\n"
        msg += f"🗂️ Category: {expense_data['category']}\n"
        msg += f"📅 Date: {formatted_date}"
        
        return msg
    
    def format_budget_confirmation(self, budget_data):
        """Format a budget confirmation message."""
        period = budget_data.get("period", "monthly").capitalize()
        category = budget_data.get("category", "all")
        amount = budget_data.get("amount", 0)
        
        # Format category description
        category_desc = f"for {category}" if category.lower() != "all" else "overall"
        
        msg = f"✅ Budget set: {period} budget {category_desc}\n"
        msg += f"💰 Amount: {amount}\n"
        
        # Add start date if available
        if "start_date" in budget_data:
            try:
                date_obj = datetime.datetime.strptime(budget_data["start_date"], "%Y-%m-%d").date()
                formatted_date = date_obj.strftime("%b %d")
                msg += f"📅 Starting: {formatted_date}"
            except:
                msg += f"📅 Starting: {budget_data['start_date']}"
        
        return msg
    
    def format_custom_period_confirmation(self, budget_data):
        """Format a custom period budget confirmation message."""
        days = budget_data.get("days", 30)
        category = budget_data.get("category", "all")
        amount = budget_data.get("amount", 0)
        
        # Format category description
        category_desc = f"for {category}" if category.lower() != "all" else "overall"
        
        msg = f"✅ Budget set: {days}-day budget {category_desc}\n"
        msg += f"💰 Amount: {amount}\n"
        
        # Add start and end dates
        if "start_date" in budget_data:
            try:
                start_date = datetime.datetime.strptime(budget_data["start_date"], "%Y-%m-%d").date()
                end_date = start_date + datetime.timedelta(days=days-1)
                
                formatted_start = start_date.strftime("%b %d")
                formatted_end = end_date.strftime("%b %d")
                
                msg += f"📅 Period: {formatted_start} to {formatted_end} ({days} days)"
            except:
                msg += f"📅 Period: {days} days starting {budget_data['start_date']}"
        
        return msg
    
    def format_budget_status(self, budget_status):
        """Format a budget status message."""
        if not budget_status.get("has_budget", False):
            return "📊 **Budget Status**\n\nNo active budget found. Set a budget first with a command like 'Set ₱1000 for next 7 days'."
        
        # Basic budget info
        period_type = budget_status["period"]["period_type"]
        
        # Format period description based on type
        if period_type == "custom":
            period_desc = f"{budget_status['period']['total_days']}-day period"
        else:
            period_desc = period_type.capitalize()
        
        # Format dates
        start_date = datetime.datetime.strptime(budget_status["period"]["start_date"], "%Y-%m-%d").strftime("%b %d")
        end_date = datetime.datetime.strptime(budget_status["period"]["end_date"], "%Y-%m-%d").strftime("%b %d")
        
        # Format the status emoji
        status_emoji = "✅"  # under_budget
        if budget_status.get("status") == "over_budget":
            status_emoji = "❌"
        elif budget_status.get("status") == "near_limit":
            status_emoji = "⚠️"
        
        # Create the response
        response = f"📊 **{period_desc} Budget Status** ({start_date} - {end_date})\n\n"
        
        # Budget overview
        response += f"{status_emoji} **Budget:** {float(budget_status['budget']['Amount']):.2f}\n"
        response += f"💰 **Spent so far:** {budget_status['total_spent']:.2f} ({budget_status['percent_used']:.1f}%)\n"
        response += f"🔢 **Remaining:** {budget_status['remaining']:.2f}\n\n"
        
        # Period progress
        days_elapsed = budget_status.get("days_elapsed", 0)
        total_days = budget_status["period"]["total_days"]
        response += f"⏳ **Period Progress:** {days_elapsed} of {total_days} days " + \
                   f"({(days_elapsed/total_days)*100:.1f}%)\n\n"
        
        # Daily breakdown
        response += "📅 **Daily Breakdown:**\n"
        response += f"• Budget per day: {budget_status['daily_budget']:.2f}\n"
        response += f"• Average spent per day: {budget_status['daily_average']:.2f}\n"
        
        if budget_status.get("days_remaining", 0) > 0:
            response += f"• Remaining daily allowance: {budget_status.get('remaining_daily_allowance', 0):.2f}\n"
        
        return response