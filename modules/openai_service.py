import json
import os
from openai import OpenAI
from modules import category_service
from config import OPENAI_API_KEY
import datetime
# Hardcoded OpenAI API key (not recommended for production)

def detect_intent(user_input):
    """
    Detect the user's intent from their natural language input.
    Improved to accurately identify expense entries.
    
    Args:
        user_input (str): Natural language input from the user
        
    Returns:
        dict: Dictionary containing intent type and relevant data
    """
    try:
        # Create a client instance
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        # Use chat completions API with improved prompt
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system", 
                    "content": "You are a financial assistant that categorizes user messages into clear intents. Your primary purpose is to distinguish expense entries from other requests."
                },
                {
                    "role": "user", 
                    "content": f"""Classify this message: '{user_input}'. 
                    Return ONLY a JSON with 'intent' and 'data'.
                    
                    Intents are strictly one of:
                    - "expense" (user is logging an expense)
                    - "summary" (user wants to see a summary of expenses)
                    - "budget_status" (user wants to check their budget status)
                    - "set_budget" (user wants to set or update a budget)
                    - "help" (user needs help)
                    - "other" (anything else)
                    
                    IMPORTANT GUIDELINES:
                    1. If the message contains a product/service name and an amount, classify as "expense"
                    2. If the message is very short with just an item and a number, it's an "expense"
                    3. Words like "summary", "report", "show me" suggest a "summary" intent
                    4. Budget-related words like "budget", "spending limit" suggest "budget_status" or "set_budget"
                    
                    Examples of "expense" intent:
                    - "puka necklace 150" -> expense
                    - "burger 250" -> expense
                    - "spent 223 on mcdonalds" -> expense
                    - "50 coffee" -> expense
                    - "dining out 500" -> expense
                    - "payment for electricity bill 1200" -> expense
                    
                    Examples of "summary" intent:
                    - "show my expenses this week" -> summary
                    - "how much did I spend last month" -> summary
                    - "give me my spending report" -> summary
                    
                    Examples of "budget_status" intent:
                    - "how's my budget" -> budget_status
                    - "am I over budget" -> budget_status
                    
                    For "expense" intent, include 'amount' and 'description' in data if possible.
                    For "summary" intent, include 'period' (e.g., 'this week', 'last month') in data.
                    For "set_budget", include 'amount' and 'period' ('weekly' or 'monthly') in data.
                    """
                }
            ],
            temperature=0
        )
        
        # Get the response content
        content = completion.choices[0].message.content
        
        # Clean the content if needed
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].strip()
            
        # Parse JSON
        intent_data = json.loads(content)
        
        return intent_data
        
    except Exception as e:
        print(f"Intent detection error: {str(e)}")
        # Default to treating input as an expense if detection fails
        return {"intent": "expense", "data": {}}

def detect_budget_command(user_input):
    """
    Detect if the user's input is a budget-related command.
    
    Args:
        user_input (str): The user's query
        
    Returns:
        bool: True if this is a budget command, False otherwise
    """
    try:
        # Create a client instance
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        # Use chat completions API
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system", 
                    "content": "You are a financial assistant that determines if a message is related to budget management."
                },
                {
                    "role": "user", 
                    "content": f"""Is this message asking to set or check a budget? '{user_input}'
                    
                    Return ONLY 'yes' or 'no'.
                    
                    Examples that would be 'yes':
                    - "Set a monthly budget of $500"
                    - "Create a budget of 1000 for food"
                    - "How am I doing on my budget?"
                    - "Budget status for this month"
                    - "Am I under budget?"
                    
                    Examples that would be 'no':
                    - "I spent $50 on dinner"
                    - "Show my expenses this week"
                    - "Add a new category"
                    """
                }
            ],
            temperature=0
        )
        
        # Get the response content
        content = completion.choices[0].message.content.strip().lower()
        
        return content == "yes"
        
    except Exception as e:
        print(f"Error detecting budget command: {str(e)}")
        return False

def extract_budget_details(user_input):
    """
    Extract budget details from natural language input using OpenAI.
    
    Args:
        user_input (str): Natural language description of a budget request
        
    Returns:
        dict: Dictionary containing amount, period, and optional category
    """
    try:
        # Create a client instance
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        # Extract budget details
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system", 
                    "content": "You are a financial assistant that extracts budget information from requests."
                },
                {
                    "role": "user", 
                    "content": f"""Extract budget information from this request: '{user_input}'
                    
                    Return ONLY a JSON with these fields:
                    - amount: the numeric budget amount (without currency symbols)
                    - period: 'weekly' or 'monthly'
                    - category: specific category name or 'Total' for overall budget
                    
                    If any field is not specified, use these defaults:
                    - period: 'monthly'
                    - category: 'Total'
                    
                    Examples:
                    Input: "Set a monthly budget of 1000"
                    Output: {{"amount": 1000, "period": "monthly", "category": "Total"}}
                    
                    Input: "I want to budget 200 per week for food"
                    Output: {{"amount": 200, "period": "weekly", "category": "Food"}}
                    
                    Input: "Create a 500 transportation budget"
                    Output: {{"amount": 500, "period": "monthly", "category": "Transportation"}}
                    """
                }
            ],
            temperature=0.1
        )
        
        # Get the response content
        content = completion.choices[0].message.content
        
        # Clean the content if needed
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].strip()
            
        # Parse JSON
        budget_data = json.loads(content)
        
        # Validate amount
        amount = float(budget_data.get("amount", 0))
        if amount <= 0:
            raise ValueError("Could not extract a valid budget amount")
        
        # Validate period
        period = budget_data.get("period", "monthly").lower()
        if period not in ["weekly", "monthly"]:
            period = "monthly"  # Default to monthly
        
        # Get category
        category = budget_data.get("category", "Total")
        
        return {
            "amount": amount,
            "period": period,
            "category": category
        }
        
    except Exception as e:
        print(f"Error extracting budget details: {str(e)}")
        raise Exception(f"Error extracting budget details: {str(e)}")

def detect_summary_request(user_input):
    """
    Specifically detect if the user is asking for an expense summary.
    
    Args:
        user_input (str): The user's query
        
    Returns:
        bool: True if this is a summary request, False otherwise
    """
    try:
        # Create a client instance
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        # Use chat completions API
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system", 
                    "content": "You are a financial assistant that determines if a message is explicitly asking for an expense summary."
                },
                {
                    "role": "user", 
                    "content": f"""Is this message asking for an expense summary or report? '{user_input}'
                    
                    Return ONLY 'yes' or 'no'.
                    
                    Examples that would be 'yes':
                    - "Show me my expenses for this month"
                    - "How much did I spend this week?"
                    - "What's my spending summary for March?"
                    - "Generate a report for last month"
                    
                    Examples that would be 'no':
                    - "I spent $50 on dinner"
                    - "Add a new category"
                    - "Delete the Travel category"
                    - "Dining out 223 mcdo"
                    - "223 mcdonalds"
                    """
                }
            ],
            temperature=0
        )
        
        # Get the response content
        content = completion.choices[0].message.content.strip().lower()
        
        return content == "yes"
        
    except Exception as e:
        print(f"Error detecting summary request: {str(e)}")
        return False

def extract_expense_details_with_date(user_input):
    """
    Extract expense details from natural language input using OpenAI, including date.
    Improved with better category mapping and handling of dining establishments.
    
    Args:
        user_input (str): Natural language description of an expense
        
    Returns:
        dict: Dictionary containing amount, category, description, and date
    """
    try:
        # Force a fresh fetch of categories
        category_service._categories_cache["last_updated"] = 0
        
        # Get available categories with descriptions
        available_categories = category_service.get_categories()
        categories_list = ", ".join(available_categories)
        
        # Create a client instance
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        # Extract expense details with improved prompt
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system", 
                    "content": f"You are a financial assistant that extracts expense details and maps them accurately to available categories: {categories_list}"
                },
                {
                    "role": "user", 
                    "content": f"""Given this expense description: '{user_input}'
                    
                    1. Extract the numeric amount (if any), ignoring currency symbols
                    2. Create a brief description for what this expense is for
                    3. Classify it into one of these available categories ONLY: {categories_list}
                    4. Extract or infer the date (use today's date if not specified)
                    
                    Today's date is {datetime.datetime.now().strftime("%Y-%m-%d")}.
                    
                    Important mapping rules:
                    - Fast food (McDonalds, Jollibee, KFC, etc.) should be categorized as "Dining out"
                    - Coffee shops should be categorized as "Beverages" or "Dining out" if available
                    - If a category isn't available, map to the closest matching category
                    
                    Return ONLY a JSON with these fields:
                    - amount: the numeric value (without currency symbols)
                    - description: a brief description of the expense
                    - category: MUST be one of the available categories listed above
                    - date: the date in YYYY-MM-DD format
                    """
                }
            ],
            temperature=0.1
        )
        
        # Get the response content
        content = completion.choices[0].message.content
        
        # Clean the content if needed
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].strip()
            
        # Parse JSON
        expense_data = json.loads(content)
        
        # Verify the category is in our available list
        if expense_data.get("category") not in available_categories:
            # Find closest match or use "Miscellaneous"
            # This is a fallback in case the model still returns an invalid category
            closest_match = "Miscellaneous"
            for cat in available_categories:
                if cat.lower() == "dining out" and "food" in expense_data.get("category", "").lower():
                    closest_match = cat
                    break
                if cat.lower() == "miscellaneous":
                    closest_match = cat
            
            print(f"Invalid category '{expense_data.get('category')}', using '{closest_match}' instead")
            expense_data["category"] = closest_match
        
        # Validate amount
        if expense_data.get("amount", 0) <= 0:
            raise ValueError("Could not extract a valid amount from the expense")
            
        # Ensure description exists
        if not expense_data.get("description"):
            expense_data["description"] = user_input
        
        return expense_data
        
    except Exception as e:
        # Print the error for debugging
        print(f"Error extracting expense details: {str(e)}")
        raise Exception(f"Error extracting expense details: {str(e)}")
    
def detect_category_spending_query(user_input):
    """
    Detect if the user is asking about spending on a specific category.
    More strict detection to avoid false positives.
    
    Args:
        user_input (str): The user's query
        
    Returns:
        tuple: (is_category_query, category, period)
            - is_category_query (bool): True if this is a category spending query
            - category (str): Extracted category name or empty string
            - period (str): Extracted time period or "this week"
    """
    try:
        # Create a client instance
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        # Get available categories for context
        available_categories = category_service.get_categories()
        categories_list = ", ".join(available_categories)
        
        # Use chat completions API with improved prompt
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system", 
                    "content": "You are a financial assistant that analyzes whether a message is specifically asking about spending history on a category, not logging a new expense."
                },
                {
                    "role": "user", 
                    "content": f"""Analyze this message: '{user_input}'
                    
                    Is the user EXPLICITLY asking about how much they spent on a specific category?
                    This should only be true if they are asking for a report or summary of past spending.
                    If they appear to be logging a new expense, this should be false.
                    
                    Available categories are: {categories_list}
                    
                    Return a JSON with these fields:
                    - is_category_query: true or false
                    - category: the category name (if applicable)
                    - period: the time period (today, this week, this month, etc.) or "this week" if not specified
                    
                    Examples of category queries (should return true):
                    - "How much did I spend on Food this week?"
                    - "Show my Transportation expenses for today"
                    - "What's my Dining out total for this month?"
                    
                    Examples of expense logging (should return false):
                    - "Dining out 223 mcdo"
                    - "50 coffee"
                    - "Transportation 20 taxi"
                    - "223 mcdonalds"
                    """
                }
            ],
            temperature=0
        )
        
        # Get the response content
        content = completion.choices[0].message.content
        
        # Clean the content if needed
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].strip()
            
        query_data = json.loads(content)
        
        return (
            query_data.get("is_category_query", False),
            query_data.get("category", ""),
            query_data.get("period", "this week")
        )
        
    except Exception as e:
        print(f"Error detecting category spending query: {str(e)}")
        return (False, "", "this week")