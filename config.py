"""
Configuration settings for the financial tracker bot.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Telegram Bot Configuration
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')

# OpenAI Configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')

# Google Sheets Configuration
SHEET_ID = os.getenv('SHEET_ID')
CREDENTIALS_FILE = os.getenv('CREDENTIALS_FILE', 'credentials.json')

# Default categories if none are defined in the spreadsheet
DEFAULT_CATEGORIES = [
    "Food", "Transportation", "Entertainment", "Housing", 
    "Utilities", "Healthcare", "Shopping", "Education", "Other"
]

# Sheets names
EXPENSES_SHEET = "Expenses"
CATEGORIES_SHEET = "Categories"
BUDGETS_SHEET = "Budgets"
PREFERENCES_SHEET = "Preferences"
DEBTS_SHEET = "Debts"  # New sheet for debt tracking

# Debug mode
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'