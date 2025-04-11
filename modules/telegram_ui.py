"""
UI module for Telegram bot interactions.
This module provides functions to create inline keyboards and format messages with reply options.
"""
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

def get_expense_keyboard():
    """
    Get an inline keyboard for expense entry follow-up actions.
    
    Returns:
        InlineKeyboardMarkup: Keyboard with expense-related actions
    """
    keyboard = [
        [
            InlineKeyboardButton("📊 Weekly Summary", callback_data="summary_week"),
            InlineKeyboardButton("💰 Check Budget", callback_data="check_budget")
        ],
        [
            InlineKeyboardButton("📋 List Categories", callback_data="list_categories"),
            InlineKeyboardButton("📅 Today's Expenses", callback_data="today_expenses")
        ]
    ]
    
    return InlineKeyboardMarkup(keyboard)

def get_summary_keyboard():
    """
    Get an inline keyboard for expense summary follow-up actions.
    Focused more on weekly summaries.
    
    Returns:
        InlineKeyboardMarkup: Keyboard with summary-related actions
    """
    keyboard = [
        [
            InlineKeyboardButton("📅 Weekly Summary", callback_data="summary_week"),
            InlineKeyboardButton("📅 This Month", callback_data="summary_month")
        ],
        [
            InlineKeyboardButton("💰 Check Budget", callback_data="check_budget"),
            InlineKeyboardButton("📅 Today's Expenses", callback_data="today_expenses")
        ]
    ]
    
    return InlineKeyboardMarkup(keyboard)

def get_budget_keyboard():
    """
    Get an inline keyboard for budget follow-up actions.
    Focused on weekly budget features.
    
    Returns:
        InlineKeyboardMarkup: Keyboard with budget-related actions
    """
    keyboard = [
        [
            InlineKeyboardButton("📊 Weekly Summary", callback_data="summary_week"),
            InlineKeyboardButton("➕ Set Weekly Budget", callback_data="set_weekly_budget")
        ],
        [
            InlineKeyboardButton("📅 Today's Expenses", callback_data="today_expenses"),
            InlineKeyboardButton("💰 Set Budget", callback_data="set_budget")
        ]
    ]
    
    return InlineKeyboardMarkup(keyboard)

def get_help_keyboard():
    """
    Get an inline keyboard for help menu options.
    
    Returns:
        InlineKeyboardMarkup: Keyboard with help-related actions
    """
    keyboard = [
        [
            InlineKeyboardButton("📅 Today's Expenses", callback_data="today_expenses"),
            InlineKeyboardButton("📊 Weekly Summary", callback_data="summary_week")
        ],
        [
            InlineKeyboardButton("💰 Budget Status", callback_data="check_budget"),
            InlineKeyboardButton("📋 Categories", callback_data="list_categories")
        ]
    ]
    
    return InlineKeyboardMarkup(keyboard)

def format_expense_response(response_text):
    """
    Format an expense entry response with follow-up options.
    
    Args:
        response_text (str): Original response text
        
    Returns:
        tuple: (formatted text, inline keyboard)
    """
    # Keep the original response 
    return response_text, get_expense_keyboard()

def format_summary_response(response_text):
    """
    Format a summary response with follow-up options.
    
    Args:
        response_text (str): Original response text
        
    Returns:
        tuple: (formatted text, inline keyboard)
    """
    # Keep the original response
    return response_text, get_summary_keyboard()

def format_budget_response(response_text):
    """
    Format a budget response with follow-up options.
    
    Args:
        response_text (str): Original response text
        
    Returns:
        tuple: (formatted text, inline keyboard)
    """
    # Keep the original response
    return response_text, get_budget_keyboard()

def get_expense_template_keyboard():
    """
    Get an inline keyboard with quick expense templates.
    
    Returns:
        InlineKeyboardMarkup: Keyboard with expense templates
    """
    keyboard = [
        [
            InlineKeyboardButton("🍔 Food", callback_data="template_food"),
            InlineKeyboardButton("🚕 Transport", callback_data="template_transport"),
            InlineKeyboardButton("🛒 Shopping", callback_data="template_shopping")
        ],
        [
            InlineKeyboardButton("💡 Utilities", callback_data="template_utilities"),
            InlineKeyboardButton("🏠 Housing", callback_data="template_housing"),
            InlineKeyboardButton("🎭 Entertainment", callback_data="template_entertainment")
        ]
    ]
    
    return InlineKeyboardMarkup(keyboard)

def get_template_text(template_type):
    """
    Get template text for quick expense entry.
    
    Args:
        template_type (str): The type of template
        
    Returns:
        str: Template text
    """
    templates = {
        "food": "Spent ₱ on food",
        "transport": "Spent ₱ on transport",
        "shopping": "Spent ₱ on shopping",
        "utilities": "Paid ₱ for utilities",
        "housing": "Paid ₱ for housing",
        "entertainment": "Spent ₱ on entertainment"
    }
    
    return templates.get(template_type, "Spent ₱ on ")

def get_category_spending_keyboard():
    """
    Get an inline keyboard for category spending follow-up actions.
    
    Returns:
        InlineKeyboardMarkup: Keyboard with category-related actions
    """
    keyboard = [
        [
            InlineKeyboardButton("📊 /sum", callback_data="summary_week"),
            InlineKeyboardButton("💰 Check Budget", callback_data="check_budget")
        ],
        [
            InlineKeyboardButton("📋 List Categories", callback_data="list_categories"),
            InlineKeyboardButton("📅 Today's Expenses", callback_data="today_expenses")
        ]
    ]
    
    return InlineKeyboardMarkup(keyboard)

def get_category_search_keyboard():
    """
    Get an inline keyboard for category search options.
    
    Returns:
        InlineKeyboardMarkup: Keyboard with category timeframe options
    """
    keyboard = [
        [
            InlineKeyboardButton("📅 Today", callback_data="cat_search_today"),
            InlineKeyboardButton("📊 This Week", callback_data="cat_search_week")
        ],
        [
            InlineKeyboardButton("⬅️ Back", callback_data="check_budget"),
        ]
    ]
    
    return InlineKeyboardMarkup(keyboard)

def get_week_start_day_keyboard():
    """
    Get an inline keyboard for selecting the week start day.
    
    Returns:
        InlineKeyboardMarkup: Keyboard with day options
    """
    keyboard = [
        [
            InlineKeyboardButton("Monday", callback_data="weekstart_0"),
            InlineKeyboardButton("Tuesday", callback_data="weekstart_1")
        ],
        [
            InlineKeyboardButton("Wednesday", callback_data="weekstart_2"),
            InlineKeyboardButton("Thursday", callback_data="weekstart_3")
        ],
        [
            InlineKeyboardButton("Friday", callback_data="weekstart_4"),
            InlineKeyboardButton("Saturday", callback_data="weekstart_5")
        ],
        [
            InlineKeyboardButton("Sunday", callback_data="weekstart_6"),
            InlineKeyboardButton("❌ Cancel", callback_data="weekstart_cancel")
        ]
    ]
    
    return InlineKeyboardMarkup(keyboard)