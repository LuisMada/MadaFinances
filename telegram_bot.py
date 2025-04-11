# telegram_bot.py
import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

# Import your existing services
from modules import expense_service, expense_summary_service, budget_service
from modules import category_service, openai_service

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

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
    await update.message.reply_text(welcome_message)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a help message when the command /help is issued."""
    help_text = (
        "📝 **How to use this bot:**\n\n"
        "**Log expenses**\n• Just type what you spent money on\n• Example: \"Spent ₱1225 on lunch yesterday\"\n\n"
        "**Get summaries**\n• Ask for expense summaries\n• Example: \"Show my expenses this week\"\n\n"
        "**Budget management**\n• Set or check budgets\n• Example: \"Set ₱5000 monthly budget\"\n\n"
        "**Categories**\n• List categories: \"/categories\"\n\n"
        "View your dashboard at: [your-render-app-url]"
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

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
            await update.message.reply_text(response, parse_mode='Markdown')
        elif is_budget_request:
            # Handle budget-related request
            try:
                budget_data = openai_service.extract_budget_details(user_input)
                
                # Check if this is setting a budget or checking status
                if "set" in user_input.lower() or "create" in user_input.lower():
                    # Set budget
                    budget_service.set_budget(budget_data["amount"], budget_data["period"], budget_data["category"])
                    
                    # Format response with proper currency symbol
                    period_display = "monthly" if budget_data["period"].lower() == "monthly" else "weekly"
                    category_display = f"for {budget_data['category']}" if budget_data["category"] != "Total" else ""
                    
                    response = f"✅ Set {period_display} budget of ₱{budget_data['amount']:.2f} {category_display}"
                else:
                    # Check budget status
                    period_data = expense_summary_service.parse_time_period("This Month")
                    budget_status = budget_service.get_budget_status(period_data["start_date"], period_data["end_date"])
                    response = budget_service.format_budget_status_response(budget_status)
                
                await update.message.reply_text(response, parse_mode='Markdown')
            except Exception as e:
                logger.error(f"Error processing budget request: {str(e)}")
                await update.message.reply_text(f"Error processing budget request: {str(e)}")
        else:
            # Assume it's an expense entry
            response = expense_service.handle_multiple_expenses(user_input)
            await update.message.reply_text(response, parse_mode='Markdown')
            
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        await update.message.reply_text("I encountered an error processing your request. Please try again.")

def main():
    """Initialize and start the bot."""
    # Create the Application
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("categories", categories_command))
    
    # Add message handler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Run the bot until the user presses Ctrl-C
    logger.info("Starting bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()