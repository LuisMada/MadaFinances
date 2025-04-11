import json
from openai import OpenAI
from modules import category_service, sheets_service
import datetime
from config import OPENAI_API_KEY

# This is the enhanced extract_expense_details_with_date function
# Replace this function in your expense_service.py file

def extract_expense_details_with_date(user_input):
    """
    Extract expense details from natural language input using OpenAI, including date.
    Enhanced to handle more date formats and complex expense descriptions.
    
    Args:
        user_input (str): Natural language description of an expense
        
    Returns:
        dict: Dictionary containing amount, category, description, and date
    """
    try:
        # Force a fresh fetch of categories by invalidating the cache
        category_service._categories_cache["last_updated"] = 0
        
        # Get categories with descriptions (same as before)
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
        
        # Extract expense details including date - ENHANCED PROMPT
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system", 
                    "content": "You are a financial assistant specializing in accurately categorizing expenses and extracting dates with precision."
                },
                {
                    "role": "user", 
                    "content": f"""Given this expense description: '{user_input}'
                    
                    1. Extract the numeric amount (if any), ignoring currency symbols (₱, $, €, etc.) and correctly handling formats like '1,500' or '2k'
                    2. Determine what this expense is for (transportation, food, etc.)
                    3. Create a brief but descriptive label for this expense
                    4. Extract or infer the date of the expense with precision (use today's date if not specified)
                    
                    Today's date is {datetime.datetime.now().strftime("%Y-%m-%d")}.
                    
                    Return ONLY a JSON with these fields:
                    - amount: the numeric value (without currency symbols)
                    - purpose: what general category this expense belongs to
                    - description: a brief description of the expense
                    - date: the date in YYYY-MM-DD format
                    
                    Handle these date formats and expressions accurately:
                    - Relative dates: "yesterday", "last Monday", "this morning", "past Tuesday", "two days ago", "day before yesterday"
                    - Absolute dates: "April 5", "05/04", "April 5th, 2025", "5/3/25", "5-Apr", "April 2025"
                    - Time references: "breakfast today", "dinner yesterday", "last night", "this morning", "lunch time"
                    - Special dates: "last weekend", "last pay day", "New Year's Eve", "Christmas"
                    
                    Handle these expense formats accurately:
                    - "spent 50 on lunch today"
                    - "50 for lunch"
                    - "bought coffee for 25 yesterday"
                    - "paid 125 for electricity bill last week"
                    - "taxi fare 80 this morning"
                    - "grabbed snacks 45"
                    - "groceries at SM 500"
                    - "₱200 for dinner with friends"
                    - "200 pesos dinner"
                    - "coffee with colleagues 350"
                    - "1,500 for rent payment"
                    - "2k for laptop repair"
                    
                    Examples:
                    Input: "spent 50 on lunch today"
                    Output: {{"amount": 50, "purpose": "food", "description": "lunch", "date": "2025-04-11"}}
                    
                    Input: "₱100 for uber yesterday"
                    Output: {{"amount": 100, "purpose": "transportation", "description": "uber ride", "date": "2025-04-10"}}
                    
                    Input: "paid 25 for coffee on April 5"
                    Output: {{"amount": 25, "purpose": "food", "description": "coffee", "date": "2025-04-05"}}
                    
                    Input: "grocery shopping 1,500 last Monday"
                    Output: {{"amount": 1500, "purpose": "food", "description": "grocery shopping", "date": "2025-04-07"}}
                    
                    Input: "electricity bill 2000"
                    Output: {{"amount": 2000, "purpose": "utilities", "description": "electricity bill", "date": "2025-04-11"}}
                    
                    Input: "2k for birthday present for mom last weekend"
                    Output: {{"amount": 2000, "purpose": "gifts", "description": "birthday present for mom", "date": "2025-04-06"}}
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
                    - Date: {purpose_data.get('date', datetime.datetime.now().strftime("%Y-%m-%d"))}
                    
                    I need to assign this expense to one of our existing expense categories.
                    Here are all the available categories with their descriptions:
                    
                    {categories_context}
                    
                    Based on the expense information, select the MOST APPROPRIATE category from the list above.
                    Return ONLY the exact name of one category from the list - nothing else.
                    
                    Pay special attention to these mappings:
                    - Food includes restaurants, groceries, snacks, drinks
                    - Transportation includes taxis, public transit, fuel
                    - Shopping includes clothes, gadgets, personal items
                    - Utilities includes electricity, water, internet, phone bills
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
        
        # Get the date (default to today if not provided)
        date = purpose_data.get('date', datetime.datetime.now().strftime("%Y-%m-%d"))
        
        # Create the final expense data
        expense_data = {
            "amount": float(purpose_data.get("amount", 0)),
            "category": category,
            "description": purpose_data.get("description", ""),
            "date": date
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

# Function to handle multiple expenses in a single input
# This is the enhanced handle_multiple_expenses function to improve multi-input support
# You would replace this function in your expense_service.py file

def handle_multiple_expenses(user_input):
    """
    Handle multiple expenses entered in a single message with improved parsing.
    
    Args:
        user_input (str): User message containing multiple expenses
        
    Returns:
        str: Response message with results of processing all expenses
    """
    try:
        # Use OpenAI to split the input into separate expense statements
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        # First, determine if this is a multi-expense input and split it - ENHANCED PROMPT
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system", 
                    "content": "You are a financial assistant that helps identify and separate expense entries with high accuracy."
                },
                {
                    "role": "user", 
                    "content": f"""
                    The following text may contain one or more expense entries:
                    
                    "{user_input}"
                    
                    If there are multiple expense entries, separate them into distinct entries.
                    Return ONLY a JSON with an 'expenses' array, where each item is a separate expense entry.
                    
                    Handle these formats carefully:
                    - Comma-separated lists: "coffee 50, lunch 200, taxi 150"
                    - Line-separated entries: expenses on separate lines
                    - Semi-colon separated entries: "coffee 50; lunch 200; taxi 150"
                    - Natural language lists: "I spent 50 on coffee and 200 on lunch"
                    - Multiple expenses with dates: "50 for lunch today and 30 for coffee yesterday"
                    - Implicit separators: "spent 100 on groceries paid 50 for taxi"
                    - Lists with conjunctions: "bought coffee for 25, lunch for 150, and a movie ticket for 200"
                    
                    Pay special attention to these challenging cases:
                    - When expenses have complex descriptions: "dinner with friends at the Italian restaurant 500"
                    - When numbers appear in descriptions: "iPhone 13 case 150"
                    - When currencies and amounts have separators: "1,500 for groceries and 2,000 for rent"
                    
                    Examples:
                    Input: "50 for lunch today and 20 for coffee yesterday"
                    Output: {{"expenses": ["50 for lunch today", "20 for coffee yesterday"]}}
                    
                    Input: "bought groceries 1,750.50, movie tickets 300, and coffee 75"
                    Output: {{"expenses": ["bought groceries 1,750.50", "movie tickets 300", "coffee 75"]}}
                    
                    Input: "paid 2k for rent and 500 for internet last week"
                    Output: {{"expenses": ["paid 2k for rent", "500 for internet last week"]}}
                    
                    Input: "spent 300 on dinner with friends on Friday and 150 on groceries on Saturday morning"
                    Output: {{"expenses": ["spent 300 on dinner with friends on Friday", "150 on groceries on Saturday morning"]}}
                    
                    If there's only one expense, still wrap it in an array.
                    Input: "paid 100 for dinner"
                    Output: {{"expenses": ["paid 100 for dinner"]}}
                    
                    Never include analytical notes or comments in your output, ONLY the JSON.
                    """
                }
            ],
            temperature=0.1
        )
        
        # Parse the response
        content = completion.choices[0].message.content
        
        # Clean the content if needed
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].strip()
            
        expenses_data = json.loads(content)
        expense_entries = expenses_data.get("expenses", [])
        
        if not expense_entries:
            return "I couldn't identify any expenses in your message. Please try again with a clearer expense description."
        
        # Process each expense entry
        results = []
        for entry in expense_entries:
            try:
                # Use the enhanced function to handle each expense with date
                expense_data = extract_expense_details_with_date(entry)
                
                if expense_data:
                    # Format the extracted data as a dictionary for sheets
                    expense_record = {
                        "Date": expense_data["date"],  # Use the extracted date
                        "Description": expense_data["description"],
                        "Amount": expense_data["amount"],
                        "Category": expense_data["category"],
                        "Source": "OpenAI"
                    }
                    
                    # Log the expense to Google Sheets
                    sheets_service.log_expense(expense_record)
                    
                    # Format the date for display
                    try:
                        # Parse the date and format it nicely
                        date_obj = datetime.datetime.strptime(expense_data["date"], "%Y-%m-%d")
                        formatted_date = date_obj.strftime("%b %d, %Y")  # e.g., "Apr 11, 2025"
                    except:
                        formatted_date = expense_data["date"]
                    
                    # Enhanced confirmation message with more details
                    confirmation = (
                        f"✅ Got it! I've recorded ₱{expense_data['amount']:.2f} for "
                        f"{expense_data['description']} in the {expense_data['category']} "
                        f"category on {formatted_date}."
                    )
                    results.append(confirmation)
                else:
                    results.append(f"❌ Couldn't process: '{entry}'")
            
            except Exception as e:
                results.append(f"❌ Error processing '{entry}': {str(e)}")
        
        # Combine results into a single response
        if len(results) == 1:
            return results[0]
        else:
            response = "I've processed your expenses:\n\n"
            for idx, result in enumerate(results, 1):
                response += f"{idx}. {result}\n"
            return response
    
    except Exception as e:
        return f"An error occurred while processing multiple expenses: {str(e)}"