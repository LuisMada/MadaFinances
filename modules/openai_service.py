import json
import os
from openai import OpenAI
from modules import category_service
from config import OPENAI_API_KEY
# Hardcoded OpenAI API key (not recommended for production)

def detect_intent(user_input):
    """
    Detect the user's intent from their natural language input.
    
    Args:
        user_input (str): Natural language input from the user
        
    Returns:
        dict: Dictionary containing intent type and relevant data
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
                    "content": "You are a financial assistant. Classify the user's intent from their message."
                },
                {
                    "role": "user", 
                    "content": f"""Classify this message: '{user_input}'. 
                    Return ONLY a JSON with 'intent' and 'data'.
                    Possible intents:
                    - expense (user is logging an expense)
                    - summary (user wants to see a summary of expenses)
                    - add_category (user wants to add a new expense category)
                    - rename_category (user wants to rename a category)
                    - delete_category (user wants to delete a category)
                    - list_categories (user wants to see all categories)
                    - set_budget (user wants to set or update a budget)
                    - budget_status (user wants to check their budget status)
                    - help (user needs help)
                    - other (anything else)
                    
                    For add_category, include 'name' and optional 'description'.
                    For rename_category, include 'old_name' and 'new_name'.
                    For delete_category, include 'name'.
                    For summary, include 'period' (e.g., 'this week', 'last month').
                    For set_budget, include 'amount', 'period' ('weekly' or 'monthly'), and optional 'category'.
                    For budget_status, include optional 'period'.
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
                    "content": "You are a financial assistant that determines if a message is asking for an expense summary."
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

def extract_expense_details(user_input):
    """
    Extract expense details from natural language input using OpenAI.
    
    Args:
        user_input (str): Natural language description of an expense
        
    Returns:
        dict: Dictionary containing amount, category, and description
    """
    try:
        # Force a fresh fetch of categories by invalidating the cache
        category_service._categories_cache["last_updated"] = 0
        
        # Get categories with descriptions
        categories_with_descriptions = {}
        try:
            # Get the client
            client = category_service.sheets_service.get_sheets_client()
            
            # Open the spreadsheet
            SHEET_ID = "10c4U63Od8Im3E2HP5NKReio6wafWbfJ_zsGJRKHB1LY"
            spreadsheet = client.open_by_key(SHEET_ID)
            
            # Get the categories sheet
            categories_sheet = spreadsheet.worksheet("Categories")
            
            # Get all rows
            all_rows = categories_sheet.get_all_values()
            
            # Skip header row and process category data
            for row in all_rows[1:]:
                if len(row) >= 1 and row[0].strip():
                    category_name = row[0].strip()
                    description = row[1].strip() if len(row) > 1 else ""
                    categories_with_descriptions[category_name] = description
        except Exception as e:
            print(f"Error fetching category descriptions: {str(e)}")
            # Fall back to just getting category names
            categories = category_service.get_categories()
            for category in categories:
                categories_with_descriptions[category] = ""
        
        # Format categories with descriptions for the prompt
        categories_context = ""
        for category, description in categories_with_descriptions.items():
            if description:
                categories_context += f"- {category}: {description}\n"
            else:
                categories_context += f"- {category}\n"
        
        # Get just the category names
        categories = list(categories_with_descriptions.keys())
        
        # Create a client instance
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        # First, determine the purpose of the expense
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system", 
                    "content": "You are a financial assistant that categorizes expenses accurately."
                },
                {
                    "role": "user", 
                    "content": f"""Given this expense description: '{user_input}'
                    
                    1. Extract the numeric amount (if any)
                    2. Determine what this expense is for (transportation, food, etc.)
                    3. Create a brief description
                    
                    Return ONLY a JSON with these fields:
                    - amount: the numeric value (without currency symbols)
                    - purpose: what general category this expense belongs to
                    - description: a brief description of the expense
                    
                    For example:
                    Input: "spent 50 on lunch"
                    Output: {{"amount": 50, "purpose": "food", "description": "lunch"}}
                    
                    Input: "100 for uber"
                    Output: {{"amount": 100, "purpose": "transportation", "description": "uber ride"}}
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
        purpose_data = json.loads(content)
        
        print(f"First-stage parsing result: {purpose_data}")
        
        # Now map the purpose to the available categories with better context
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system", 
                    "content": "You are a financial assistant that categorizes expenses accurately."
                },
                {
                    "role": "user", 
                    "content": f"""
                    Original expense: "{user_input}"
                    
                    I've extracted this information:
                    - Amount: {purpose_data.get('amount', 'unknown')}
                    - Purpose: {purpose_data.get('purpose', 'unknown')}
                    - Description: {purpose_data.get('description', 'unknown')}
                    
                    I need to assign this expense to one of our existing expense categories.
                    Here are all the available categories with their descriptions:
                    
                    {categories_context}
                    
                    Based on the expense information, select the MOST APPROPRIATE category from the list above.
                    Return ONLY the exact name of one category from the list - nothing else.
                    """
                }
            ],
            temperature=0
        )
        
        # Get the category
        category = completion.choices[0].message.content.strip()
        
        # Clean the category (remove quotes and other formatting)
        if category.startswith('"') and category.endswith('"'):
            category = category[1:-1]
            
        # Ensure the category is in our list, otherwise default to "Other"
        if category not in categories:
            print(f"Category '{category}' not found in available categories. Using 'Other'.")
            category = "Other"
        
        # Create the final expense data
        expense_data = {
            "amount": float(purpose_data.get("amount", 0)),
            "category": category,
            "description": purpose_data.get("description", "")
        }
        
        print(f"Final expense data: {expense_data}")
        
        # Validate required fields
        if expense_data["amount"] <= 0:
            raise ValueError("Could not extract a valid amount from the expense")
            
        if not expense_data["description"]:
            expense_data["description"] = user_input
        
        return expense_data
        
    except Exception as e:
        # Print the error for debugging
        print(f"OpenAI API Error: {str(e)}")
        raise Exception(f"Error extracting expense details: {str(e)}")
    
def detect_category_spending_query(user_input):
    """
    Detect if the user is asking about spending on a specific category.
    
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
        
        # Use chat completions API
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system", 
                    "content": "You are a financial assistant that analyzes whether a message is asking about spending on a specific category."
                },
                {
                    "role": "user", 
                    "content": f"""Analyze this message: '{user_input}'
                    
                    Is the user asking about how much they spent on a specific category?
                    If yes, identify the category and time period.
                    
                    Return a JSON with these fields:
                    - is_category_query: true or false
                    - category: the category name (if applicable)
                    - period: the time period (today, this week, this month, etc.) or "this week" if not specified
                    
                    Examples:
                    Input: "How much did I spend on food this week?"
                    Output: {{"is_category_query": true, "category": "Food", "period": "this week"}}
                    
                    Input: "What are my transportation expenses for today?"
                    Output: {{"is_category_query": true, "category": "Transportation", "period": "today"}}
                    
                    Input: "Show my expenses for last month"
                    Output: {{"is_category_query": false, "category": "", "period": "last month"}}
                    
                    Input: "I spent 100 on coffee"
                    Output: {{"is_category_query": false, "category": "", "period": "this week"}}
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
            
        query_data = json.loads(content)
        
        return (
            query_data.get("is_category_query", False),
            query_data.get("category", ""),
            query_data.get("period", "this week")
        )
        
    except Exception as e:
        print(f"Error detecting category spending query: {str(e)}")
        return (False, "", "this week")