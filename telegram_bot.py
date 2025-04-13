"""
Financial Tracker Bot
Main entry point for the Telegram bot.
"""
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, 
    CommandHandler, 
    MessageHandler, 
    CallbackQueryHandler,
    ConversationHandler,
    filters, 
    ContextTypes
)
import traceback
import os
import datetime

from config import TELEGRAM_TOKEN, DEBUG
from services.ai_agent import AIAgent
from services.expense import ExpenseService
from services.budget import BudgetService
from services.summary import SummaryService
from ui.telegram_ui import TelegramUI

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation states
AWAITING_BUDGET_AMOUNT = 1
AWAITING_CUSTOM_DAYS = 2
AWAITING_CUSTOM_BUDGET = 3

# Initialize services
ai_agent = AIAgent()
expense_service = ExpenseService()
budget_service = BudgetService()
summary_service = SummaryService()
ui = TelegramUI()

# Simple HTTP request handler for Render
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'Bot is running!')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /start command with simplified interface.
    
    Args:
        update (Update): The update object
        context (ContextTypes.DEFAULT_TYPE): The context object
    """
    user = update.effective_user
    
    await update.message.reply_text(
        f"Hi {user.first_name}! I'm your Financial Tracker Bot.\n\n"
        f"• Type expenses like 'coffee 3.50' to log them\n"
        f"• Set a budget with 'set 300 budget for 14 days'\n"
        f"• Use the buttons below to view expenses or get help",
        reply_markup=ui.get_main_keyboard()
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /help command.
    
    Args:
        update (Update): The update object
        context (ContextTypes.DEFAULT_TYPE): The context object
    """
    await update.message.reply_text(
        ui.format_help_message(),
        parse_mode='Markdown',
        reply_markup=ui.get_main_keyboard()
    )

async def custom_budget_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /cb command to set custom period budgets (simplified version).
    
    Args:
        update (Update): The update object
        context (ContextTypes.DEFAULT_TYPE): The context object
    """
    await update.message.reply_text(
        "📅 **Set a Custom Period Budget**\n\n"
        "Select the number of days for your budget period:",
        parse_mode='Markdown',
        reply_markup=ui.get_custom_period_keyboard()
    )
    
    return AWAITING_CUSTOM_DAYS

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle incoming messages.
    
    Args:
        update (Update): The update object
        context (ContextTypes.DEFAULT_TYPE): The context object
    """
    user_input = update.message.text
    
    if DEBUG:
        logger.info(f"Received message: {user_input}")
    
    # Check if we're waiting for budget input
    if context.user_data.get('awaiting_budget'):
        return await handle_budget_input(update, context)
    
    # Check if we're waiting for custom budget days
    if context.user_data.get('awaiting_custom_days'):
        return await handle_custom_days_input(update, context)
    
    # Check if we're waiting for custom budget amount
    if context.user_data.get('awaiting_custom_budget'):
        return await handle_custom_budget_input(update, context)
    
    # Detect intent using AI
    intent_data = ai_agent.detect_intent(user_input)
    
    if DEBUG:
        logger.info(f"Detected intent: {intent_data}")
    
    # Process based on intent
    if intent_data["intent"] == "expense":
        result = expense_service.process_expense(user_input)
        
        if result["success"]:
            # Check if we processed multiple expenses
            if "multiple" in result["data"] and result["data"]["multiple"]:
                await update.message.reply_text(
                    f"✅ {result['message']}",
                    reply_markup=ui.get_main_keyboard()
                )
            else:
                # Single expense
                await update.message.reply_text(
                    ui.format_expense_confirmation(result["data"]),
                    reply_markup=ui.get_main_keyboard()
                )
        else:
            await update.message.reply_text(
                f"❌ {result['message']}",
                reply_markup=ui.get_main_keyboard()
            )
    
    elif intent_data["intent"] == "summary":
        await update.message.reply_text("Generating summary, please wait...")
        
        result = summary_service.generate_summary(user_input)
        
        if result["success"]:
            await update.message.reply_text(
                result["message"],
                reply_markup=ui.get_main_keyboard()
            )
        else:
            await update.message.reply_text(
                f"❌ {result['message']}",
                reply_markup=ui.get_main_keyboard()
            )
    
    elif intent_data["intent"] == "budget_status":
        await update.message.reply_text("Checking budget status, please wait...")
        
        result = budget_service.get_budget_status(user_input)
        
        if result["success"]:
            await update.message.reply_text(
                ui.format_budget_status(result["data"]),
                reply_markup=ui.get_main_keyboard()
            )
        else:
            await update.message.reply_text(
                f"❌ {result['message']}",
                reply_markup=ui.get_main_keyboard()
            )
    
    elif intent_data["intent"] == "set_budget":
        result = budget_service.set_budget(user_input)
        
        if result["success"]:
            # Format message based on period type
            budget_data = result["data"]
            if budget_data.get("period") == "custom":
                # Custom period budget confirmation
                await update.message.reply_text(
                    ui.format_custom_period_confirmation(budget_data),
                    reply_markup=ui.get_main_keyboard()
                )
            else:
                # Regular budget confirmation
                await update.message.reply_text(
                    ui.format_budget_confirmation(budget_data),
                    reply_markup=ui.get_main_keyboard()
                )
        else:
            await update.message.reply_text(
                f"❌ {result['message']}",
                reply_markup=ui.get_main_keyboard()
            )
    
    elif intent_data["intent"] == "delete_expense":
        result = expense_service.delete_expense(user_input)
        
        if result["success"]:
            await update.message.reply_text(
                f"✅ {result['message']}",
                reply_markup=ui.get_main_keyboard()
            )
        else:
            await update.message.reply_text(
                f"❌ {result['message']}",
                reply_markup=ui.get_main_keyboard()
            )
    
    elif intent_data["intent"] == "help":
        await update.message.reply_text(
            ui.format_help_message(),
            parse_mode='Markdown',
            reply_markup=ui.get_main_keyboard()
        )
    
    else:  # "other" or unrecognized intent
        await update.message.reply_text(
            "I'm not sure what you want to do. You can log an expense by typing something like 'coffee 3.50', "
            "or use one of the options below:",
            reply_markup=ui.get_main_keyboard()
        )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Button handler that uses the date field from expenses for filtering.
    
    Args:
        update (Update): The update object
        context (ContextTypes.DEFAULT_TYPE): The context object
    """
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    
    if DEBUG:
        logger.info(f"Button pressed: {callback_data}")
    
    if callback_data == "todays_expenses":
        await query.edit_message_text("Fetching today's expenses...")
        
        try:
            # Get today's date
            today = datetime.datetime.now().date()
            today_str = today.strftime("%Y-%m-%d")
            
            # Get all recent expenses
            # We'll get the last week of expenses and filter by date string
            one_week_ago = today - datetime.timedelta(days=7)
            all_expenses = expense_service.sheets.get_expenses_in_date_range(
                start_date=one_week_ago,
                end_date=today
            )
            
            # Filter expenses that have today's date in their Date field
            todays_expenses = []
            for expense in all_expenses:
                # Get the date from the expense data
                expense_date = expense.get('Date', '')
                
                # Check if it's today's date
                if expense_date == today_str:
                    todays_expenses.append(expense)
            
            # Try to get budget information, but don't fail if it's not available
            budget_data = None
            try:
                budget_status = budget_service.get_budget_status()
                if budget_status and budget_status.get("success", False):
                    budget_data = budget_status.get("data", {})
            except Exception as e:
                logger.error(f"Error getting budget status: {str(e)}")
                # Continue without budget data
            
            # Format and send the message
            message = ui.format_todays_expenses(todays_expenses, budget_data)
            
            await query.edit_message_text(
                message,
                parse_mode='Markdown',
                reply_markup=ui.get_main_keyboard()
            )
        except Exception as e:
            logger.error(f"Error handling today's expenses: {str(e)}")
            traceback.print_exc()
            await query.edit_message_text(
                f"Error fetching expenses: {str(e)}",
                reply_markup=ui.get_main_keyboard()
            )
    
    elif callback_data == "help":
        try:
            await query.edit_message_text(
                ui.format_help_message(),
                parse_mode='Markdown',
                reply_markup=ui.get_main_keyboard()
            )
        except Exception as e:
            logger.error(f"Error displaying help: {str(e)}")
            await query.edit_message_text(
                "Error displaying help. Please try again.",
                reply_markup=ui.get_main_keyboard()
            )
    
    else:
        # Default fallback
        await query.edit_message_text(
            "Please select an option:",
            reply_markup=ui.get_main_keyboard()
        )
        # Default fallback
        await query.edit_message_text(
            "Please select an option:",
            reply_markup=ui.get_main_keyboard()
        )

async def handle_budget_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle budget amount input.
    
    Args:
        update (Update): The update object
        context (ContextTypes.DEFAULT_TYPE): The context object
    """
    user_input = update.message.text
    period = context.user_data.get('budget_period', 'monthly')
    
    # Reset the awaiting flag
    context.user_data['awaiting_budget'] = False
    
    # Process the budget setting
    modified_input = f"set {period} budget {user_input}"
    result = budget_service.set_budget(modified_input)
    
    if result["success"]:
        await update.message.reply_text(
            ui.format_budget_confirmation(result["data"]),
            reply_markup=ui.get_main_keyboard()
        )
    else:
        await update.message.reply_text(
            f"❌ {result['message']}",
            reply_markup=ui.get_main_keyboard()
        )
    
    return ConversationHandler.END

async def handle_custom_days_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle custom period days input (simplified version).
    
    Args:
        update (Update): The update object
        context (ContextTypes.DEFAULT_TYPE): The context object
    """
    user_input = update.message.text
    
    try:
        # Try to parse the days as an integer
        days = int(user_input)
        
        if days < 1 or days > 365:
            await update.message.reply_text(
                "Please enter a valid number of days between 1 and 365.",
                reply_markup=ui.get_main_keyboard()
            )
            return AWAITING_CUSTOM_DAYS
        
        # Store the days and update state
        context.user_data['custom_budget_days'] = days
        context.user_data['awaiting_custom_days'] = False
        context.user_data['awaiting_custom_budget'] = True
        
        await update.message.reply_text(
            f"Please enter the amount for your {days}-day budget:"
        )
        
        return AWAITING_CUSTOM_BUDGET
        
    except ValueError:
        await update.message.reply_text(
            "Please enter a valid number of days.",
            reply_markup=ui.get_main_keyboard()
        )
        return AWAITING_CUSTOM_DAYS

async def handle_custom_budget_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle custom budget amount input (simplified version).
    
    Args:
        update (Update): The update object
        context (ContextTypes.DEFAULT_TYPE): The context object
    """
    user_input = update.message.text
    days = context.user_data.get('custom_budget_days', 30)  # Default to 30 if not set
    
    # Reset the awaiting flag
    context.user_data['awaiting_custom_budget'] = False
    
    try:
        # Simple parsing - just extract the first number as the amount
        amount = 0
        category = "all"
        
        parts = user_input.split()
        for part in parts:
            try:
                amount = float(part.replace(',', ''))
                break  # Take the first valid number as amount
            except ValueError:
                continue
        
        # Check if a category is mentioned
        categories = budget_service.sheets.get_categories()
        for cat in categories:
            if cat.lower() in user_input.lower():
                category = cat
                break
        
        # Create a budget data dictionary
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        budget_data = {
            "amount": amount,
            "period": "custom",
            "days": days,
            "category": category,
            "start_date": today,
            "active": True
        }
        
        # Set the budget
        result = budget_service.set_budget(budget_data)
        
        if result["success"]:
            await update.message.reply_text(
                ui.format_custom_period_confirmation(result["data"]),
                reply_markup=ui.get_main_keyboard()
            )
        else:
            await update.message.reply_text(
                f"❌ {result['message']}",
                reply_markup=ui.get_main_keyboard()
            )
    except Exception as e:
        logger.error(f"Error setting custom budget: {str(e)}")
        traceback.print_exc()
        await update.message.reply_text(
            f"❌ Error setting budget: {str(e)}",
            reply_markup=ui.get_main_keyboard()
        )
    
    # Clean up user data
    if 'custom_budget_days' in context.user_data:
        del context.user_data['custom_budget_days']
    
    return ConversationHandler.END

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Log errors and send a message to the user.
    
    Args:
        update (Update): The update object
        context (ContextTypes.DEFAULT_TYPE): The context object
    """
    logger.error(msg="Exception while handling an update:", exc_info=context.error)
    traceback.print_exc()
    
    # Send a message to the user
    error_message = "Sorry, something went wrong. Please try again later."
    
    if update.effective_message:
        await update.effective_message.reply_text(error_message)

def main():
    """Start the bot with simplified functionality."""
    # Create the Application
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    
    # Add regular button handler
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Add message handler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    # Set up webhook if in production
    webhook_url = os.environ.get("WEBHOOK_URL")
    webhook_port = int(os.environ.get("PORT", 8443))
    
    if webhook_url:
        application.run_webhook(
            listen="0.0.0.0",
            port=webhook_port,
            url_path=TELEGRAM_TOKEN,
            webhook_url=f"{webhook_url}/{TELEGRAM_TOKEN}"
        )
    else:
        # Start the Bot in polling mode
        application.run_polling()

if __name__ == '__main__':
    main()