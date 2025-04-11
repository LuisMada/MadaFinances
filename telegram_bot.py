# telegram_bot.py
import os
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from dotenv import load_dotenv
import datetime

# Import your existing services
from modules import expense_service, expense_summary_service, budget_service
from modules import category_service, openai_service, telegram_ui, preference_service

if not logging.getLogger().handlers:
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
logger = logging.getLogger(__name__)

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# Simple HTTP request handler for Render
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'Bot is running!')

# Function to start HTTP server
def start_http_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), SimpleHTTPRequestHandler)
    logger.info(f'Starting HTTP server on port {port}')
    server.serve_forever()

# Command handlers
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a welcome message when the command /start is issued."""
    user_id = update.effective_user.id
    
    # Set default week start day preference if not already set
    if preference_service.get_user_preference(user_id, "week_start_day") is None:
        preference_service.set_week_start_day(user_id, 0)  # Default to Monday
    
    welcome_message = (
        "👋 Welcome to your Financial Tracker!\n\n"
        "You can:\n"
        "• Log expenses like \"spent 500 on lunch\"\n"
        "• Get summaries with \"show expenses this week\"\n"
        "• Set budgets with \"set 5000 monthly budget\"\n"
        "• Change settings with \"/weekstart\" to set week start day\n\n"
        "Type /help for more information."
    )
    # Add inline keyboard for quick actions
    keyboard = telegram_ui.get_help_keyboard()
    await update.message.reply_text(welcome_message, reply_markup=keyboard)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a help message when the command /help is issued."""
    help_text = (
        "📝 **How to use this bot:**\n\n"
        "**Log expenses**\n• Just type what you spent money on\n• Example: \"Spent ₱1225 on lunch yesterday\"\n\n"
        "**Get summaries**\n• Ask for expense summaries\n• Example: \"Show my expenses this week\"\n\n"
        "**Budget management**\n• Set or check budgets\n• Example: \"Set ₱5000 monthly budget\"\n\n"
        "**Categories**\n• List categories: \"/categories\"\n\n"
        "**Preferences**\n• Set week start day: \"/weekstart\"\n\n"
        "**Shortcuts**\n"
        "• /sum - Show this week's expenses\n"
        "• /b - Check budget status\n"
        "• /e - Quick expense entry template\n\n"
        "View your dashboard at: [your-render-app-url]"
    )
    # Add inline keyboard for quick actions
    keyboard = telegram_ui.get_help_keyboard()
    await update.message.reply_text(help_text, parse_mode='Markdown', reply_markup=keyboard)

async def categories_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all available expense categories."""
    try:
        categories = category_service.get_categories()
        if not categories:
            await update.message.reply_text("No categories found.")
            return
            
        categories_list = "\n".join([f"• {category}" for category in categories])
        await update.message.reply_text(f"📋 **Available categories:**\n{categories_list}", parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error listing categories: {str(e)}")
        await update.message.reply_text(f"Error listing categories: {str(e)}")

async def summary_shortcut_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shortcut command to show expense summary for this week."""
    user_id = update.effective_user.id
    logger.info(f"Summary shortcut requested by {user_id}")
    
    try:
        # Get user's preferred week start day
        week_start_index = preference_service.get_week_start_day(user_id)
        
        # Calculate the current week's start and end using the user's preference
        today = datetime.date.today()
        days_since_week_start = (today.weekday() - week_start_index) % 7
        start_of_week = today - datetime.timedelta(days=days_since_week_start)
        end_of_week = start_of_week + datetime.timedelta(days=6)
        
        # Get expenses for the current week based on user's preference
        df = expense_summary_service.get_expenses_in_period(start_of_week, end_of_week)
        
        # Generate summary
        summary = expense_summary_service.generate_summary(df)
        
        # Create period info with custom week start day
        weekday_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        week_start_day = weekday_names[week_start_index] if 0 <= week_start_index <= 6 else "Monday"
        
        period = {
            "start_date": start_of_week,
            "end_date": end_of_week,
            "period_name": f"This Week (Starting {week_start_day})"
        }
        
        # Format the response
        response = expense_summary_service.format_summary_response(summary, period)
        
        # Add detailed list of expenses if there are any
        if not df.empty:
            # Sort by date (newest first)
            df_sorted = df.sort_values('Date', ascending=False)
            
            # Format the detailed list
            response += "\n\n**Detailed Expenses:**\n"
            
            for _, row in df_sorted.iterrows():
                date_str = row['Date'].strftime("%b %d") if hasattr(row['Date'], 'strftime') else str(row['Date'])
                amount = float(row['Amount'])
                description = row['Description']
                category = row['Category']
                response += f"• {date_str}: ₱{amount:.2f} - {description} ({category})\n"
        
        # Send the response
        formatted_text, keyboard = telegram_ui.format_summary_response(response)
        await update.message.reply_text(formatted_text, parse_mode='Markdown', reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Error generating summary via shortcut: {str(e)}")
        await update.message.reply_text(f"Error generating summary: {str(e)}")

async def budget_shortcut_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shortcut command to check budget status with weekly focus."""
    user_id = update.effective_user.id
    logger.info(f"Budget status shortcut requested by {user_id}")
    
    try:
        # Get user's preferred week start day
        week_start_index = preference_service.get_week_start_day(user_id)
        
        # Use weekly period for budget status
        today = datetime.date.today()
        # Calculate the current week's start and end using the user's preference
        days_since_week_start = (today.weekday() - week_start_index) % 7
        start_of_week = today - datetime.timedelta(days=days_since_week_start)
        end_of_week = start_of_week + datetime.timedelta(days=6)
        
        # Get budget status using the week dates and week start preference
        budget_status = budget_service.get_budget_status(start_of_week, end_of_week, week_start_index=week_start_index)
        
        # Format with enhanced weekly focus
        response = format_weekly_budget_status(budget_status)
        
        # Use the budget keyboard for response
        formatted_text, keyboard = telegram_ui.format_budget_response(response)
        await update.message.reply_text(formatted_text, parse_mode='Markdown', reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Error checking budget status via shortcut: {str(e)}")
        await update.message.reply_text(f"Error checking budget status: {str(e)}")

def format_weekly_budget_status(budget_status):
    """
    Format the budget status into a weekly-focused, readable response.
    Includes today's spending and remaining daily allowance.
    
    Args:
        budget_status (dict): Dictionary containing budget information
        
    Returns:
        str: Formatted response string
    """
    if not budget_status.get("has_budget", False):
        return "📊 **Weekly Budget Status**\n\nNo budgets found. Set a budget first with a command like 'Set ₱1000 weekly budget'."
    
    # Get week start day name
    week_start_index = budget_status.get("week_start_index", 0)  # Default to Monday (0)
    weekday_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    week_start_day = weekday_names[week_start_index] if 0 <= week_start_index <= 6 else "Monday"
    
    # Create a well-formatted summary focused on the weekly view
    response = f"📊 **Weekly Budget Status** (Weeks start on {week_start_day})\n\n"
    
    # Get today's date
    today = datetime.date.today()
    
    # Format the status emoji
    status_emoji = "✅"  # under_budget
    if budget_status.get("status") == "over_budget":
        status_emoji = "❌"
    elif budget_status.get("status") == "near_limit":
        status_emoji = "⚠️"
    
    # Weekly budget info
    response += f"{status_emoji} **Weekly Budget:** ₱{budget_status.get('weekly_budget', 0):.2f}\n"
    response += f"💰 **Spent so far:** ₱{budget_status['total_spent']:.2f} ({budget_status['percent_used']:.1f}%)\n"
    response += f"🔢 **Remaining:** ₱{budget_status['remaining']:.2f}\n"
    
    # Week progress
    days_elapsed = budget_status.get("days_elapsed", 0)
    days_in_week = 7
    response += f"⏳ **Week Progress:** {days_elapsed} of {days_in_week} days " + \
               f"({(days_elapsed/days_in_week)*100:.1f}%)\n\n"
    
    # Get today's expenses
    try:
        # Use the existing expense_summary_service to get today's expenses
        today_expenses_df = expense_summary_service.get_expenses_in_period(today, today)
        today_total = today_expenses_df['Amount'].sum() if not today_expenses_df.empty else 0
        
        # Add today's spending info
        response += f"📅 **Today's Spending:** ₱{today_total:.2f}\n"
        
        # Calculate remaining for today
        daily_budget = budget_status.get('daily_budget', 0)
        remaining_today = daily_budget - today_total
        remaining_color = "surplus" if remaining_today >= 0 else "over budget"
        response += f"📅 **Today's Budget:** ₱{daily_budget:.2f} " + \
                   f"(₱{abs(remaining_today):.2f} {remaining_color})\n\n"
    except Exception as e:
        logger.error(f"Error calculating today's expenses: {str(e)}")
        response += "📅 **Today's Spending:** Could not calculate\n\n"
    
    # Daily averages
    response += "📅 **Daily Breakdown:**\n"
    response += f"• Budget per day: ₱{budget_status['daily_budget']:.2f}\n"
    response += f"• Average spent per day: ₱{budget_status['daily_average']:.2f}\n"
    
    if budget_status.get("days_remaining", 0) > 0:
        response += f"• Remaining daily allowance: ₱{budget_status.get('remaining_daily_allowance', 0):.2f}\n\n"
    else:
        response += "\n"
    
    return response

async def expense_template_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shortcut command to show expense entry template."""
    template_message = (
        "📝 **Quick Expense Entry**\n\n"
        "Reply with your expense in any of these formats:\n"
        "• spent 500 on lunch\n"
        "• 1200 for electricity bill yesterday\n"
        "• 50 coffee\n\n"
        "Or choose a template below:"
    )
    # Add keyboard with expense templates
    keyboard = telegram_ui.get_expense_template_keyboard()
    await update.message.reply_text(template_message, parse_mode='Markdown', reply_markup=keyboard)

async def weekstart_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /weekstart command to set the week start day."""
    user_id = update.effective_user.id
    logger.info(f"Week start day setting requested by {user_id}")
    
    # Get current week start day
    current_start_day = preference_service.get_week_start_day(user_id)
    
    # Map day index to day name
    weekday_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    current_day_name = weekday_names[current_start_day] if 0 <= current_start_day <= 6 else "Monday"
    
    # Create message with current setting
    message = (
        f"📅 **Week Start Day Settings**\n\n"
        f"Your current week starts on: **{current_day_name}**\n\n"
        f"Select a new start day for your week:"
    )
    
    # Add keyboard with day options
    keyboard = telegram_ui.get_week_start_day_keyboard()
    await update.message.reply_text(message, parse_mode='Markdown', reply_markup=keyboard)

# telegram_bot.py (fixed button callback function)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button press from inline keyboards."""
    query = update.callback_query
    user_id = update.effective_user.id
    
    # Always answer the callback query to stop the loading animation
    await query.answer()
    
    logger.info(f"Button pressed by {user_id}: {query.data}")
    
    try:
        # Handle different button callbacks
        if query.data.startswith("summary_"):
            # Handle "Weekly Summary" button by calling the /sum command function
            if query.data == "summary_week":
                # Get user's preferred week start day
                week_start_index = preference_service.get_week_start_day(user_id)
                
                # Calculate the current week's start and end using the user's preference
                today = datetime.date.today()
                days_since_week_start = (today.weekday() - week_start_index) % 7
                start_of_week = today - datetime.timedelta(days=days_since_week_start)
                end_of_week = start_of_week + datetime.timedelta(days=6)
                
                # Get expenses for the current week based on user's preference
                df = expense_summary_service.get_expenses_in_period(start_of_week, end_of_week)
                
                # Generate summary
                summary = expense_summary_service.generate_summary(df)
                
                # Create period info with custom week start day
                weekday_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                week_start_day = weekday_names[week_start_index] if 0 <= week_start_index <= 6 else "Monday"
                
                period = {
                    "start_date": start_of_week,
                    "end_date": end_of_week,
                    "period_name": f"This Week (Starting {week_start_day})"
                }
                
                # Format the response
                response = expense_summary_service.format_summary_response(summary, period)
                
                # Add detailed list of expenses if there are any
                if not df.empty:
                    # Sort by date (newest first)
                    df_sorted = df.sort_values('Date', ascending=False)
                    
                    # Format the detailed list
                    response += "\n\n**Detailed Expenses:**\n"
                    
                    for _, row in df_sorted.iterrows():
                        date_str = row['Date'].strftime("%b %d") if hasattr(row['Date'], 'strftime') else str(row['Date'])
                        amount = float(row['Amount'])
                        description = row['Description']
                        category = row['Category']
                        response += f"• {date_str}: ₱{amount:.2f} - {description} ({category})\n"
                
                # Send the response using query.message instead of update.message
                formatted_text, keyboard = telegram_ui.format_summary_response(response)
                await query.message.reply_text(formatted_text, parse_mode='Markdown', reply_markup=keyboard)
            else:
                # Handle other summary requests
                period = query.data.replace("summary_", "")
                period_text = "this " + period
                if period == "last_month":
                    period_text = "last month"
                    
                _, response, _ = expense_summary_service.handle_expense_summary(f"Show my expenses {period_text}")
                formatted_text, keyboard = telegram_ui.format_summary_response(response)
                await query.message.reply_text(formatted_text, parse_mode='Markdown', reply_markup=keyboard)
            
        elif query.data == "today_expenses":
            # Get today's expenses
            today = datetime.date.today()
            df = expense_summary_service.get_expenses_in_period(today, today)
            
            if df.empty:
                response = "📅 **Today's Expenses**\n\nNo expenses recorded for today."
            else:
                # Format expenses in a readable way
                total = df['Amount'].sum()
                expense_list = []
                
                for _, row in df.iterrows():
                    amount = float(row['Amount'])
                    description = row['Description']
                    category = row['Category']
                    expense_list.append(f"• ₱{amount:.2f} - {description} ({category})")
                
                expenses_text = "\n".join(expense_list)
                response = f"📅 **Today's Expenses**\n\n{expenses_text}\n\n**Total:** ₱{total:.2f}"
            
            # Use summary keyboard for follow-up options
            _, keyboard = telegram_ui.format_summary_response(response)
            await query.message.reply_text(response, parse_mode='Markdown', reply_markup=keyboard)
            
        elif query.data == "check_budget":
            # Budget status check with weekly focus
            today = datetime.date.today()
            
            # Get user's preferred week start day
            week_start_index = preference_service.get_week_start_day(user_id)
            
            # Calculate the current week's start and end using the user's preference
            days_since_week_start = (today.weekday() - week_start_index) % 7
            start_of_week = today - datetime.timedelta(days=days_since_week_start)
            end_of_week = start_of_week + datetime.timedelta(days=6)
            
            # Get budget status using the week dates and week start preference
            budget_status = budget_service.get_budget_status(start_of_week, end_of_week, week_start_index=week_start_index)
            
            # Get today's expenses for the daily budget update
            today_expenses_df = expense_summary_service.get_expenses_in_period(today, today)
            today_total = today_expenses_df['Amount'].sum() if not today_expenses_df.empty else 0
            
            # Add today's spending to the budget_status
            budget_status["today_spent"] = today_total
            
            # Format with weekly focus
            response = budget_service.format_weekly_budget_status_response(budget_status)
            
            # Use the budget keyboard for response
            formatted_text, keyboard = telegram_ui.format_budget_response(response)
            await query.message.reply_text(formatted_text, parse_mode='Markdown', reply_markup=keyboard)
            
        elif query.data.startswith("set_") and "budget" in query.data:
            # Budget setting template
            period = "monthly"
            if "weekly" in query.data:
                period = "weekly"
                
            template_message = f"To set a {period} budget, reply with an amount like:\n\n" + \
                               f"\"Set ₱5000 {period} budget\"\n\n" + \
                               f"Or for a specific category:\n\n" + \
                               f"\"Set ₱1000 {period} budget for Food\""
                               
            await query.message.reply_text(template_message)
            
        elif query.data == "add_expense":
            # Expense template
            template_message = (
                "📝 **Quick Expense Entry**\n\n"
                "Reply with your expense in any of these formats:\n"
                "• spent 500 on lunch\n"
                "• 1200 for electricity bill yesterday\n"
                "• 50 coffee\n\n"
                "Or choose a template below:"
            )
            # Add keyboard with expense templates
            keyboard = telegram_ui.get_expense_template_keyboard()
            await query.message.reply_text(template_message, parse_mode='Markdown', reply_markup=keyboard)
            
        elif query.data == "list_categories":
            # List categories
            categories = category_service.get_categories()
            if not categories:
                await query.message.reply_text("No categories found.")
                return
                
            categories_list = "\n".join([f"• {category}" for category in categories])
            await query.message.reply_text(f"📋 **Available categories:**\n{categories_list}", parse_mode='Markdown')
            
        elif query.data.startswith("template_"):
            # Send expense template
            template_type = query.data.replace("template_", "")
            template_text = telegram_ui.get_template_text(template_type)
            await query.message.reply_text(f"_Complete this expense:_\n\n`{template_text}`", parse_mode='Markdown')
            
        elif query.data.startswith("weekstart_"):
            # Handle week start day setting
            action = query.data.replace("weekstart_", "")
            
            if action == "cancel":
                await query.message.reply_text("Week start day change cancelled.")
                return
                
            try:
                # Convert to day index
                day_index = int(action)
                
                if 0 <= day_index <= 6:
                    # Save preference
                    success = preference_service.set_week_start_day(user_id, day_index)
                    
                    # Map day index to day name
                    weekday_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                    day_name = weekday_names[day_index]
                    
                    if success:
                        await query.message.reply_text(f"✅ Week start day set to **{day_name}**. Your weekly summaries and budgets will now use this setting.", parse_mode='Markdown')
                    else:
                        await query.message.reply_text(f"❌ Failed to set week start day. Please try again.")
                else:
                    await query.message.reply_text(f"❌ Invalid day selected. Please try again.")
            except ValueError:
                await query.message.reply_text(f"❌ Invalid selection. Please try again.")
            
    except Exception as e:
        logger.error(f"Error handling button callback: {str(e)}")
        await query.message.reply_text(f"Error processing your request: {str(e)}")

# Message handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process user messages and respond appropriately."""
    user_input = update.message.text
    user_id = update.effective_user.id
    logger.info(f"Received message from {user_id}: {user_input}")
    
    try:
        # Check if this is a category spending query using the new detector
        is_category_query, category, period = openai_service.detect_category_spending_query(user_input)
        
        if is_category_query:
            # Handle category-specific spending query
            await handle_category_spending_query(update, category, period)
            return
            
        # Check if this is a summary request
        is_summary_request = openai_service.detect_summary_request(user_input)
        
        # Check if this is a budget request
        is_budget_request = openai_service.detect_budget_command(user_input)
        
        # Process based on intent
        if is_summary_request:
            # Handle expense summary request
            _, response, _ = expense_summary_service.handle_expense_summary(user_input)
            formatted_text, keyboard = telegram_ui.format_summary_response(response)
            await update.message.reply_text(formatted_text, parse_mode='Markdown', reply_markup=keyboard)
        elif is_budget_request:
            # Handle budget-related request
            try:
                budget_data = openai_service.extract_budget_details(user_input)
                
                # Check if this is setting a budget or checking status
                if "set" in user_input.lower() or "create" in user_input.lower():
                    # Set budget
                    budget_service.set_budget(budget_data["amount"], budget_data["period"], budget_data["category"])
                    
                    # Format category for display
                    category_display = "overall spending"
                    if budget_data["category"] != "Total":
                        category_display = f"the {budget_data['category']} category"
                    
                    # Enhanced budget confirmation
                    response = (
                        f"✅ Got it! I've set a {budget_data['period'].lower()} budget of "
                        f"₱{budget_data['amount']:.2f} for {category_display}. "
                        f"I'll track your spending against this budget."
                    )
                else:
                    # Check budget status with weekly focus
                    today = datetime.date.today()
                    
                    # Get user's preferred week start day
                    week_start_index = preference_service.get_week_start_day(user_id)
                    
                    # Calculate the current week's start and end using the user's preference
                    days_since_week_start = (today.weekday() - week_start_index) % 7
                    start_of_week = today - datetime.timedelta(days=days_since_week_start)
                    end_of_week = start_of_week + datetime.timedelta(days=6)
                    
                    # Get budget status using the week dates and week start preference
                    budget_status = budget_service.get_budget_status(start_of_week, end_of_week, week_start_index=week_start_index)
                    
                    # Get today's expenses for the daily budget update
                    today_expenses_df = expense_summary_service.get_expenses_in_period(today, today)
                    today_total = today_expenses_df['Amount'].sum() if not today_expenses_df.empty else 0
                    
                    # Add today's spending to the budget_status
                    budget_status["today_spent"] = today_total
                    
                    # Format with weekly focus
                    response = budget_service.format_weekly_budget_status_response(budget_status)
                
                formatted_text, keyboard = telegram_ui.format_budget_response(response)
                await update.message.reply_text(formatted_text, parse_mode='Markdown', reply_markup=keyboard)
            except Exception as e:
                logger.error(f"Error processing budget request: {str(e)}")
                await update.message.reply_text(f"Error processing budget request: {str(e)}")
        else:
            # Assume it's an expense entry
            response = expense_service.handle_multiple_expenses(user_input)
            formatted_text, keyboard = telegram_ui.format_expense_response(response)
            await update.message.reply_text(formatted_text, parse_mode='Markdown', reply_markup=keyboard)
            
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        await update.message.reply_text("I encountered an error processing your request. Please try again.")

async def handle_category_spending_query(update: Update, category: str, period: str):
    """
    Handle queries about spending on specific categories.
    
    Args:
        update: The Telegram update
        category: Category to check spending for
        period: Time period to check (today, this week, etc.)
    """
    try:
        user_id = update.effective_user.id
        
        # Validate category exists in our system
        available_categories = category_service.get_categories()
        if category not in available_categories:
            # Try to find the closest match
            category_lower = category.lower()
            for avail_category in available_categories:
                if category_lower in avail_category.lower() or avail_category.lower() in category_lower:
                    category = avail_category
                    break
            else:  # No match found
                await update.message.reply_text(f"I couldn't find the '{category}' category. Available categories are: {', '.join(available_categories)}")
                return
                
        # Parse the time period
        period_data = expense_summary_service.parse_time_period(period)
        start_date = period_data["start_date"]
        end_date = period_data["end_date"]
        
        # Get category spending data
        spending_data = budget_service.get_category_spending(start_date, end_date, category)
        
        # Format the response
        response = budget_service.format_category_spending_response(spending_data)
        
        # Use category spending keyboard for follow-up actions
        formatted_text, keyboard = telegram_ui.format_summary_response(response)
        await update.message.reply_text(formatted_text, parse_mode='Markdown', reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error handling category spending query: {str(e)}")
        await update.message.reply_text(f"I encountered an error processing your category spending query: {str(e)}")

def main():
    """Initialize and start the bot."""
    # Start the HTTP server in a separate thread
    http_thread = threading.Thread(target=start_http_server, daemon=True)
    http_thread.start()
    logger.info("HTTP server thread started")
    
    # Create the Application
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("categories", categories_command))
    
    # Add shortcut command handlers
    application.add_handler(CommandHandler("sum", summary_shortcut_command))
    application.add_handler(CommandHandler("b", budget_shortcut_command))
    application.add_handler(CommandHandler("e", expense_template_command))
    application.add_handler(CommandHandler("weekstart", weekstart_command))
    
    # Add callback query handler for inline keyboards
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Add message handler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Run the bot until the user presses Ctrl-C
    logger.info("Starting bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()