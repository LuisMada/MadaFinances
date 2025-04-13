"""
Financial Tracker Bot
Main entry point for the Telegram bot.
"""
import logging
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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /start command.
    
    Args:
        update (Update): The update object
        context (ContextTypes.DEFAULT_TYPE): The context object
    """
    user = update.effective_user
    
    await update.message.reply_text(
        f"Hi {user.first_name}! I'm your AI Financial Tracker. I can help you track expenses, "
        f"set budgets, and analyze your spending.\n\n"
        f"Just type an expense like 'coffee 3.50' to get started!\n"
        f"Or select an option from the menu below:",
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
    Handle /cb command to set custom period budgets.
    
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
    Handle button callbacks.
    
    Args:
        update (Update): The update object
        context (ContextTypes.DEFAULT_TYPE): The context object
    """
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    
    if DEBUG:
        logger.info(f"Button pressed: {callback_data}")
    
    # Main menu options
    if callback_data == "main_menu":
        await query.edit_message_text(
            "Please select an option:",
            reply_markup=ui.get_main_keyboard()
        )
    
    elif callback_data == "summary":
        await query.edit_message_text(
            "Select a time period for your summary:",
            reply_markup=ui.get_summary_keyboard()
        )
    
    elif callback_data == "budget":
        await query.edit_message_text(
            "Budget options:",
            reply_markup=ui.get_budget_keyboard()
        )
    
    elif callback_data == "delete_expense":
        await query.edit_message_text(
            "To delete an expense, please type a message like:\n\n"
            "`delete coffee expense`\n"
            "`remove taxi payment`",
            parse_mode='Markdown',
            reply_markup=ui.get_main_keyboard()
        )
    
    elif callback_data == "help":
        await query.edit_message_text(
            ui.format_help_message(),
            parse_mode='Markdown',
            reply_markup=ui.get_main_keyboard()
        )
    
    # Summary options
    elif callback_data.startswith("summary_"):
        period = callback_data.replace("summary_", "")
        
        await query.edit_message_text("Generating summary, please wait...")
        
        # Generate summary based on selected period
        result = summary_service.generate_summary(f"Summary for {period}")
        
        if result["success"]:
            await query.edit_message_text(
                result["message"],
                reply_markup=ui.get_main_keyboard()
            )
        else:
            await query.edit_message_text(
                f"❌ {result['message']}",
                reply_markup=ui.get_main_keyboard()
            )
    
    # Budget options
    elif callback_data == "budget_status":
        await query.edit_message_text("Checking budget status, please wait...")
        
        result = budget_service.get_budget_status()
        
        if result["success"]:
            await query.edit_message_text(
                ui.format_budget_status(result["data"]),
                reply_markup=ui.get_main_keyboard()
            )
        else:
            await query.edit_message_text(
                f"❌ {result['message']}",
                reply_markup=ui.get_main_keyboard()
            )
    
    # Custom period budget options
    elif callback_data == "set_custom_budget":
        await query.edit_message_text(
            "📅 **Set a Custom Period Budget**\n\n"
            "Select the number of days for your budget period:",
            parse_mode='Markdown',
            reply_markup=ui.get_custom_period_keyboard()
        )
        
        return AWAITING_CUSTOM_DAYS
    
    elif callback_data.startswith("set_custom_budget_"):
        # Extract days from callback data
        days = callback_data.replace("set_custom_budget_", "")
        
        # Store the days in user data
        context.user_data['custom_budget_days'] = int(days)
        context.user_data['awaiting_custom_budget'] = True
        
        await query.edit_message_text(
            f"Please enter the amount for your {days}-day budget:\n"
            f"(e.g., 1000 for overall budget or 200 food for category budget)",
            reply_markup=None
        )
        
        return AWAITING_CUSTOM_BUDGET
    
    elif callback_data.startswith("set_"):
        # Extract period from callback data
        period = callback_data.replace("set_", "").replace("_budget", "")
        
        # Store the period in user data
        context.user_data['awaiting_budget'] = True
        context.user_data['budget_period'] = period
        
        await query.edit_message_text(
            f"Please enter the amount for your {period} budget:\n"
            f"(e.g., 1000 for overall budget or 200 food for category budget)",
            reply_markup=None
        )
        
        return AWAITING_BUDGET_AMOUNT

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
    Handle custom period days input.
    
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
            f"Please enter the amount for your {days}-day budget:\n"
            f"(e.g., 1000 for overall budget or 200 food for category budget)"
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
    Handle custom budget amount input with direct budget data construction.
    
    Args:
        update (Update): The update object
        context (ContextTypes.DEFAULT_TYPE): The context object
    """
    user_input = update.message.text
    days = context.user_data.get('custom_budget_days', 30)  # Default to 30 if not set
    
    # Reset the awaiting flag
    context.user_data['awaiting_custom_budget'] = False
    
    try:
        # Parse the input to extract amount and optional category
        amount = 0
        category = "all"
        
        # Simple parsing logic - first number is the amount
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
        
        # Create a budget data dictionary directly instead of parsing through AI
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        budget_data = {
            "amount": amount,
            "period": "custom",
            "days": days,
            "category": category,
            "start_date": today
        }
        
        # Set the budget using the budget service
        result = budget_service.set_budget(budget_data)
        
        if result["success"]:
            # Format for display
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
    """Start the bot."""
    # Create the Application
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Add conversation handler for budget setting
    conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(button_handler, pattern=r"^set_")
        ],
        states={
            AWAITING_BUDGET_AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_budget_input)
            ],
            AWAITING_CUSTOM_DAYS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_custom_days_input),
                CallbackQueryHandler(button_handler, pattern=r"^set_custom_budget_\d+$")
            ],
            AWAITING_CUSTOM_BUDGET: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_custom_budget_input)
            ],
        },
        fallbacks=[CommandHandler("cancel", start)],
        name="budget_conversation",
        persistent=False,
    )
    
    # Add custom budget command handler
    custom_budget_handler = ConversationHandler(
        entry_points=[CommandHandler("cb", custom_budget_command)],
        states={
            AWAITING_CUSTOM_DAYS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_custom_days_input),
                CallbackQueryHandler(button_handler, pattern=r"^set_custom_budget_\d+$")
            ],
            AWAITING_CUSTOM_BUDGET: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_custom_budget_input)
            ],
        },
        fallbacks=[CommandHandler("cancel", start)],
        name="custom_budget_conversation",
        persistent=False,
    )
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    
    # Add conversation handlers
    application.add_handler(custom_budget_handler)
    application.add_handler(conv_handler)
    
    # Add regular button handler (for buttons not in the conversation)
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