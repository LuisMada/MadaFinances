"""
Financial Tracker Bot
Main entry point for the Telegram bot.
"""
import threading
import uuid
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from services.debt import DebtService
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
AWAITING_DEBT_PERSON = 4
AWAITING_DEBT_AMOUNT = 5
AWAITING_DEBT_DIRECTION = 6
AWAITING_DEBT_DESCRIPTION = 7

# Initialize services
ai_agent = AIAgent()
expense_service = ExpenseService()
budget_service = BudgetService()
summary_service = SummaryService()
debt_service = DebtService()
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
        f"• Track debts with '200 hotdog (john)' when someone owes you\n"
        f"• Use '200 lunch - mary' when you owe someone\n"
        f"• Check balances with '/balance'\n"
        f"• Use the buttons below for quick access:",
        reply_markup=ui.get_main_keyboard()
    )

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /balance command to show debt balances.
    
    Args:
        update (Update): The update object
        context (ContextTypes.DEFAULT_TYPE): The context object
    """
    result = debt_service.list_all_balances()
    
    if result["success"]:
        await update.message.reply_text(
            ui.format_balance_summary(result["data"]),
            parse_mode='Markdown',
            reply_markup=ui.get_debt_keyboard()
        )
    else:
        await update.message.reply_text(
            f"❌ {result['message']}",
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
        ui.format_help_message_with_debt(),
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

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle incoming messages.
    
    Args:
        update (Update): The update object
        context (ContextTypes.DEFAULT_TYPE): The context object
    """
    # Refresh current date at the start of every message processing
    current_date = datetime.datetime.now().strftime("%Y-%m-%d")
    if DEBUG:
        logger.info(f"Current date: {current_date}")
    
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
    
    # Check if we're waiting for debt person input
    if context.user_data.get('awaiting_debt_person'):
        return await handle_debt_person_input(update, context)
    
    # Check if we're waiting for debt amount input
    if context.user_data.get('awaiting_debt_amount'):
        return await handle_debt_amount_input(update, context)
    
    # Check if we're waiting for debt direction input
    if context.user_data.get('awaiting_debt_direction'):
        return await handle_debt_direction_input(update, context)
    
    # Check if we're waiting for debt description input
    if context.user_data.get('awaiting_debt_description'):
        return await handle_debt_description_input(update, context)
    
    # Check if we're waiting for settlement person input
    if context.user_data.get('awaiting_settlement_person'):
        return await handle_debt_person_input(update, context)
    
    # Check if we're waiting for settlement amount input
    if context.user_data.get('awaiting_settlement_amount'):
        return await handle_debt_amount_input(update, context)
    
    # DIRECT PATTERN MATCHING: Check for settlement pattern before AI processing
    import re
    settle_match = re.search(r'settle\s+(\w+)\s+(\d+)', user_input.lower())
    if settle_match:
        if DEBUG:
            logger.info(f"Found direct settlement pattern")
        
        person = settle_match.group(1)
        amount = float(settle_match.group(2))
        
        # Create settlement data
        settlement_data = {
            "person": person.lower(),
            "amount": amount,
            "date": datetime.datetime.now().strftime("%Y-%m-%d")
        }
        
        # Process settlement directly
        result = debt_service.settle_debt(settlement_data)
        
        if result["success"]:
            await update.message.reply_text(
                ui.format_settlement_confirmation(result["data"]),
                reply_markup=ui.get_debt_keyboard()
            )
        else:
            await update.message.reply_text(
                f"❌ {result['message']}",
                reply_markup=ui.get_debt_keyboard()
            )
        return  # Exit early
    
    # DIRECT PATTERN MATCHING: Check for parentheses pattern before AI processing
    parentheses_match = re.search(r'\(([^)]+)\)', user_input)
    if parentheses_match:
        if DEBUG:
            logger.info(f"Found parentheses pattern - direct debt processing")
        
        # Extract person and description
        person = parentheses_match.group(1)
        # Extract description
        description = user_input.split('(')[0].strip()
        # Find amount 
        amount_match = re.search(r'\d+', description)
        if amount_match:
            amount = float(amount_match.group(0))
            # Description without the amount
            desc_words = description.split()
            description = ' '.join([w for w in desc_words if not w.isdigit()])
            
            # Create debt data
            debt_data = {
                "id": str(uuid.uuid4()),
                "person": person.lower(),
                "amount": amount,
                "description": description.strip(),
                "direction": "from",
                "date": datetime.datetime.now().strftime("%Y-%m-%d"),
                "status": "active"
            }
            
            if DEBUG:
                logger.info(f"Created debt data: {debt_data}")
            
            # Process debt directly
            result = debt_service.sheets.record_debt(debt_data)
            
            if result:
                await update.message.reply_text(
                    ui.format_debt_confirmation(debt_data),
                    reply_markup=ui.get_debt_keyboard()
                )
            else:
                await update.message.reply_text(
                    f"❌ Error recording debt",
                    reply_markup=ui.get_main_keyboard()
                )
            return  # Exit early, don't continue to AI intent detection
    
    # DIRECT PATTERN MATCHING: Check for dash pattern before AI processing
    dash_match = re.search(r'(\d+\s+[^-]+)\s+-\s+(\w+)', user_input)
    if dash_match:
        if DEBUG:
            logger.info(f"Found dash pattern - direct debt processing")
        
        # Extract person and description
        description_part = dash_match.group(1).strip()
        person = dash_match.group(2).strip()
        
        # Find amount
        amount_match = re.search(r'\d+', description_part)
        if amount_match:
            amount = float(amount_match.group(0))
            # Description without the amount
            desc_words = description_part.split()
            description = ' '.join([w for w in desc_words if not w.isdigit()])
            
            # Create debt data
            debt_data = {
                "id": str(uuid.uuid4()),
                "person": person.lower(),
                "amount": amount,
                "description": description.strip(),
                "direction": "to",
                "date": datetime.datetime.now().strftime("%Y-%m-%d"),
                "status": "active"
            }
            
            # Process debt directly
            result = debt_service.sheets.record_debt(debt_data)
            
            if result:
                await update.message.reply_text(
                    ui.format_debt_confirmation(debt_data),
                    reply_markup=ui.get_debt_keyboard()
                )
            else:
                await update.message.reply_text(
                    f"❌ Error recording debt",
                    reply_markup=ui.get_main_keyboard()
                )
            return  # Exit early, don't continue to AI intent detection
    
    # Detect intent using AI
    intent_data = ai_agent.detect_intent(user_input)
    
    if DEBUG:
        logger.info(f"Detected intent: {intent_data}")
    
    # Process based on intent
    if intent_data["intent"] == "expense":
        # Process as a personal expense with fresh date
        result = expense_service.process_expense(user_input, current_date)

        
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
    
    elif intent_data["intent"] == "debt_add":
        # Process as a debt only, not as an expense
        result = debt_service.add_debt(user_input)
        
        if result["success"]:
            await update.message.reply_text(
                ui.format_debt_confirmation(result["data"]),
                reply_markup=ui.get_debt_keyboard()
            )
        else:
            await update.message.reply_text(
                f"❌ {result['message']}",
                reply_markup=ui.get_main_keyboard()
            )
    
    # Add this case to the intent handling section of handle_message
    elif intent_data["intent"] == "date_query":
        # Extract the date reference
        date_reference = intent_data.get("data", {}).get("date_reference", "")
        
        if not date_reference:
            await update.message.reply_text(
                "I couldn't understand which date you're asking about. Please try again with a specific date.",
                reply_markup=ui.get_main_keyboard()
            )
            return
        
        # Get expenses for the specified date
        expenses = expense_service.sheets.get_expenses_for_date_reference(date_reference)
        
        if not expenses:
            await update.message.reply_text(
                f"No expenses found for {date_reference}.",
                reply_markup=ui.get_main_keyboard()
            )
        else:
            # Calculate total
            total = sum(float(exp.get('Amount', 0)) for exp in expenses)
            
            # Format message with list of expenses
            message = f"📅 Expenses for {date_reference}:\n\n"
            
            for i, expense in enumerate(expenses, 1):
                description = expense.get('Description', 'Unknown')
                amount = expense.get('Amount', '0')
                category = expense.get('Category', 'Other')
                message += f"{i}. {description} - {amount} ({category})\n"
            
            message += f"\nTotal: {total:.2f}"
            
            await update.message.reply_text(
                message,
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
    
    elif intent_data["intent"] == "debt_settle":
        result = debt_service.settle_debt(user_input)
        
        if result["success"]:
            await update.message.reply_text(
                ui.format_settlement_confirmation(result["data"]),
                reply_markup=ui.get_debt_keyboard()
            )
        else:
            await update.message.reply_text(
                f"❌ {result['message']}",
                reply_markup=ui.get_main_keyboard()
            )
    
    elif intent_data["intent"] == "debt_balance":
        # Check if a specific person was mentioned
        person = intent_data.get("data", {}).get("person")
        
        if person:
            # Get balance for specific person
            result = debt_service.get_balance(person)
        else:
            # Get all balances
            result = debt_service.list_all_balances()
        
        if result["success"]:
            if person:
                # Single person balance
                await update.message.reply_text(
                    result["message"],
                    reply_markup=ui.get_debt_keyboard()
                )
            else:
                # All balances
                await update.message.reply_text(
                    ui.format_balance_summary(result["data"]),
                    parse_mode='Markdown',
                    reply_markup=ui.get_debt_keyboard()
                )
        else:
            await update.message.reply_text(
                f"❌ {result['message']}",
                reply_markup=ui.get_main_keyboard()
            )
            
    elif intent_data["intent"] == "help":
        await update.message.reply_text(
            ui.format_help_message_with_debt(),
            parse_mode='Markdown',
            reply_markup=ui.get_main_keyboard()
        )
    
    else:  # "other" or unrecognized intent
        await update.message.reply_text(
            "I'm not sure what you want to do. You can log an expense by typing something like 'coffee 3.50', "
            "track debts with '200 hotdog (john)', "
            "or use one of the options below:",
            reply_markup=ui.get_main_keyboard()
        )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Button handler that handles expense filtering and debt tracking options.
    
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
    
    elif callback_data == "all_balances":
        await query.edit_message_text("Fetching balances...")
        
        try:
            result = debt_service.list_all_balances()
            
            if result["success"]:
                await query.edit_message_text(
                    ui.format_balance_summary(result["data"]),
                    parse_mode='Markdown',
                    reply_markup=ui.get_debt_keyboard()
                )
            else:
                await query.edit_message_text(
                    f"Error fetching balances: {result['message']}",
                    reply_markup=ui.get_main_keyboard()
                )
        except Exception as e:
            logger.error(f"Error handling balances: {str(e)}")
            traceback.print_exc()
            await query.edit_message_text(
                f"Error fetching balances: {str(e)}",
                reply_markup=ui.get_main_keyboard()
            )
    
    elif callback_data == "add_debt":
        # Start the conversation flow for adding a debt
        await query.edit_message_text(
            "Who is the debt with? Please enter the person's name:",
            reply_markup=None
        )
        context.user_data['awaiting_debt_person'] = True
        return AWAITING_DEBT_PERSON
    
    elif callback_data == "settle_debt":
        # Start the conversation flow for settling a debt
        await query.edit_message_text(
            "Who are you settling a debt with? Please enter the person's name:",
            reply_markup=None
        )
        context.user_data['awaiting_settlement_person'] = True
        return AWAITING_DEBT_PERSON
    
    elif callback_data == "main_menu":
        # Return to main menu
        await query.edit_message_text(
            "Please select an option:",
            reply_markup=ui.get_main_keyboard()
        )
    
    elif callback_data.startswith("set_custom_budget_"):
        # Extract days from callback data
        try:
            days = int(callback_data.split("_")[-1])
            
            # Store the days and update state
            context.user_data['custom_budget_days'] = days
            context.user_data['awaiting_custom_days'] = False
            context.user_data['awaiting_custom_budget'] = True
            
            await query.edit_message_text(
                f"Please enter the amount for your {days}-day budget:"
            )
            
            return AWAITING_CUSTOM_BUDGET
        except ValueError:
            if callback_data == "set_custom_budget_input":
                await query.edit_message_text(
                    "Please enter the number of days for your budget period:"
                )
                context.user_data['awaiting_custom_days'] = True
                return AWAITING_CUSTOM_DAYS
            else:
                await query.edit_message_text(
                    "Invalid custom budget option. Please try again.",
                    reply_markup=ui.get_main_keyboard()
                )
    
    else:
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

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Log errors and send a message to the user.
    
    Args:
        update (Update): The update object (may be None)
        context (ContextTypes.DEFAULT_TYPE): The context object
    """
    logger.error(msg="Exception while handling an update:", exc_info=context.error)
    traceback.print_exc()
    
    # Send a message to the user if possible
    error_message = "Sorry, something went wrong. Please try again later."
    
    # Check if update exists and has a message
    if update is not None and hasattr(update, 'effective_message') and update.effective_message:
        try:
            await update.effective_message.reply_text(error_message)
        except Exception as e:
            logger.error(f"Failed to send error message: {e}")

async def handle_debt_person_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle person name input for debt tracking.
    
    Args:
        update (Update): The update object
        context (ContextTypes.DEFAULT_TYPE): The context object
    """
    user_input = update.message.text
    
    # Store the person name
    context.user_data['debt_person'] = user_input.strip().lower()
    
    # Reset the awaiting flag
    if 'awaiting_debt_person' in context.user_data:
        context.user_data['awaiting_debt_person'] = False
        
        # Now ask for the amount
        await update.message.reply_text(
            f"How much is the debt with {user_input}?"
        )
        context.user_data['awaiting_debt_amount'] = True
        return AWAITING_DEBT_AMOUNT
    
    elif 'awaiting_settlement_person' in context.user_data:
        context.user_data['awaiting_settlement_person'] = False
        
        # Check if the person has active debts
        result = debt_service.get_balance(user_input)
        
        if not result["success"] or result["data"]["balance"] == 0:
            await update.message.reply_text(
                f"No active debts found with {user_input}.",
                reply_markup=ui.get_main_keyboard()
            )
            return ConversationHandler.END
        
        # Store the direction based on the balance
        balance = result["data"]["balance"]
        if balance > 0:  # They owe you
            context.user_data['debt_direction'] = "from"
        else:  # You owe them
            context.user_data['debt_direction'] = "to"
        
        # Now ask for the settlement amount
        await update.message.reply_text(
            f"How much are you settling with {user_input}? " +
            f"(Current balance: {abs(balance)}, " +
            f"{'they owe you' if balance > 0 else 'you owe them'})"
        )
        context.user_data['awaiting_settlement_amount'] = True
        return AWAITING_DEBT_AMOUNT
    
    return ConversationHandler.END

async def handle_debt_amount_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle amount input for debt tracking.
    
    Args:
        update (Update): The update object
        context (ContextTypes.DEFAULT_TYPE): The context object
    """
    user_input = update.message.text
    
    try:
        # Try to parse the amount as a number
        amount = float(user_input.replace(',', ''))
        
        # Store the amount
        context.user_data['debt_amount'] = amount
        
        # Reset the awaiting flags
        if 'awaiting_debt_amount' in context.user_data:
            context.user_data['awaiting_debt_amount'] = False
            
            # Now ask for the direction
            await update.message.reply_text(
                f"Is this debt something where:\n" +
                f"1. {context.user_data['debt_person']} owes you (they owe you)\n" +
                f"2. You owe {context.user_data['debt_person']} (you owe them)\n\n" +
                f"Please enter 1 or 2:"
            )
            context.user_data['awaiting_debt_direction'] = True
            return AWAITING_DEBT_DIRECTION
        
        elif 'awaiting_settlement_amount' in context.user_data:
            context.user_data['awaiting_settlement_amount'] = False
            
            # Process the settlement
            person = context.user_data['debt_person']
            direction = context.user_data['debt_direction']
            
            # Prepare settlement data
            settlement_data = {
                "person": person,
                "amount": amount,
                "direction": direction,
                "date": datetime.datetime.now().strftime("%Y-%m-%d")
            }
            
            # Process the settlement
            result = debt_service.settle_debt(settlement_data)
            
            if result["success"]:
                await update.message.reply_text(
                    ui.format_settlement_confirmation(result["data"]),
                    reply_markup=ui.get_debt_keyboard()
                )
            else:
                await update.message.reply_text(
                    f"❌ {result['message']}",
                    reply_markup=ui.get_main_keyboard()
                )
            
            # Clean up user data
            for key in ['debt_person', 'debt_amount', 'debt_direction']:
                if key in context.user_data:
                    del context.user_data[key]
            
            return ConversationHandler.END
        
    except ValueError:
        await update.message.reply_text(
            "Please enter a valid number for the amount.",
            reply_markup=ui.get_main_keyboard()
        )
        return AWAITING_DEBT_AMOUNT

async def handle_debt_direction_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle direction input for debt tracking.
    
    Args:
        update (Update): The update object
        context (ContextTypes.DEFAULT_TYPE): The context object
    """
    user_input = update.message.text
    
    # Parse the direction
    if user_input.strip() == "1":
        # They owe you
        context.user_data['debt_direction'] = "from"
    elif user_input.strip() == "2":
        # You owe them
        context.user_data['debt_direction'] = "to"
    else:
        await update.message.reply_text(
            "Please enter either 1 (they owe you) or 2 (you owe them)."
        )
        return AWAITING_DEBT_DIRECTION
    
    # Reset the awaiting flag
    context.user_data['awaiting_debt_direction'] = False
    
    # Now ask for the description
    await update.message.reply_text(
        "What is this debt for? (Optional, press Skip if none)"
    )
    context.user_data['awaiting_debt_description'] = True
    return AWAITING_DEBT_DESCRIPTION

async def handle_debt_description_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle description input for debt tracking.
    
    Args:
        update (Update): The update object
        context (ContextTypes.DEFAULT_TYPE): The context object
    """
    user_input = update.message.text
    
    # Store the description
    if user_input.lower() == "skip":
        context.user_data['debt_description'] = ""
    else:
        context.user_data['debt_description'] = user_input
    
    # Reset the awaiting flag
    context.user_data['awaiting_debt_description'] = False
    
    # Now process the debt
    try:
        # Prepare debt data
        debt_data = {
            "person": context.user_data['debt_person'],
            "amount": context.user_data['debt_amount'],
            "direction": context.user_data['debt_direction'],
            "description": context.user_data['debt_description'],
            "date": datetime.datetime.now().strftime("%Y-%m-%d")
        }
        
        # Add the debt
        result = debt_service.add_debt(debt_data)
        
        if result["success"]:
            await update.message.reply_text(
                ui.format_debt_confirmation(result["data"]),
                reply_markup=ui.get_debt_keyboard()
            )
        else:
            await update.message.reply_text(
                f"❌ {result['message']}",
                reply_markup=ui.get_main_keyboard()
            )
        
        # Clean up user data
        for key in ['debt_person', 'debt_amount', 'debt_direction', 'debt_description']:
            if key in context.user_data:
                del context.user_data[key]
        
        return ConversationHandler.END
        
    except Exception as e:
        await update.message.reply_text(
            f"Error adding debt: {str(e)}",
            reply_markup=ui.get_main_keyboard()
        )
        return ConversationHandler.END


def main():
    """Start the bot with proper configuration for Render."""
    # Create the Application (without the non-existent parameter)
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
 
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("balance", balance_command))  # New balance command

    # Add custom budget handler
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
    application.add_handler(custom_budget_handler)

    # Add debt tracking conversation handler
    debt_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(button_handler, pattern=r"^add_debt$"),
            CallbackQueryHandler(button_handler, pattern=r"^settle_debt$")
        ],
        states={
            AWAITING_DEBT_PERSON: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_debt_person_input)
            ],
            AWAITING_DEBT_AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_debt_amount_input)
            ],
            AWAITING_DEBT_DIRECTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_debt_direction_input)
            ],
            AWAITING_DEBT_DESCRIPTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_debt_description_input)
            ],
        },
        fallbacks=[CommandHandler("cancel", start)],
        name="debt_conversation",
        persistent=False,
    )
    application.add_handler(debt_handler)

    # Add callback query handler for buttons
    application.add_handler(CallbackQueryHandler(button_handler))

    # Add default message handler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Add error handler
    application.add_error_handler(error_handler)

    # Set up webhook if in production
    webhook_url = os.environ.get("WEBHOOK_URL")
    webhook_port = int(os.environ.get("PORT", 8443))

    if webhook_url:
        # Delete any existing webhook and drop pending updates to avoid conflicts
        print("Setting up webhook and dropping pending updates...")
        try:
            application.bot.delete_webhook(drop_pending_updates=True)
        except Exception as e:
            print(f"Error deleting webhook: {str(e)}")
        
        application.run_webhook(
            listen="0.0.0.0",
            port=webhook_port,
            url_path=TELEGRAM_TOKEN,
            webhook_url=f"{webhook_url}/{TELEGRAM_TOKEN}",
            drop_pending_updates=True
        )
    else:
        # Start a simple HTTP server in a separate thread
        server_port = int(os.environ.get("PORT", 8080))
        server = HTTPServer(('0.0.0.0', server_port), SimpleHTTPRequestHandler)
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()
        print(f"Started HTTP server on port {server_port}")
        
        # Start the Bot in polling mode with drop_pending_updates
        print("Starting polling and dropping pending updates...")
        application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()