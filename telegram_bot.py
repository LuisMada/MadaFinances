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
from modules import category_service, openai_service, telegram_ui

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
    welcome_message = (
        "👋 Welcome to your Financial Tracker!\n\n"
        "You can:\n"
        "• Log expenses like \"spent 500 on lunch\"\n"
        "• Get summaries with \"show expenses this week\"\n"
        "• Set budgets with \"set 5000 monthly budget\"\n\n"
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
    logger.info(f"Summary shortcut requested by {update.effective_user.id}")
    
    try:
        # Use existing summary service with default period
        _, response, _ = expense_summary_service.handle_expense_summary("Show my expenses this week")
        formatted_text, keyboard = telegram_ui.format_summary_response(response)
        await update.message.reply_text(formatted_text, parse_mode='Markdown', reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Error generating summary via shortcut: {str(e)}")
        await update.message.reply_text(f"Error generating summary: {str(e)}")

async def budget_shortcut_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shortcut command to check budget status."""
    logger.info(f"Budget status shortcut requested by {update.effective_user.id}")
    
    try:
        # Use existing budget status check logic
        period_data = expense_summary_service.parse_time_period("This Month")
        budget_status = budget_service.get_budget_status(period_data["start_date"], period_data["end_date"])
        response = budget_service.format_budget_status_response(budget_status)
        formatted_text, keyboard = telegram_ui.format_budget_response(response)
        await update.message.reply_text(formatted_text, parse_mode='Markdown', reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Error checking budget status via shortcut: {str(e)}")
        await update.message.reply_text(f"Error checking budget status: {str(e)}")

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

# Callback query handler for inline keyboards
# Add this function to your telegram_bot.py file, replacing the existing button_callback function

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
            # Summary requests
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
            # Budget status check
            period_data = expense_summary_service.parse_time_period("This Month")
            budget_status = budget_service.get_budget_status(period_data["start_date"], period_data["end_date"])
            response = budget_service.format_budget_status_response(budget_status)
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
            await expense_template_command(update, context)
            
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
                    # Check budget status
                    period_data = expense_summary_service.parse_time_period("This Month")
                    budget_status = budget_service.get_budget_status(period_data["start_date"], period_data["end_date"])
                    response = budget_service.format_budget_status_response(budget_status)
                
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
    
    # Add callback query handler for inline keyboards
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Add message handler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Run the bot until the user presses Ctrl-C
    logger.info("Starting bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()