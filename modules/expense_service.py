import json
from openai import OpenAI
from modules import category_service, sheets_service
import datetime
from config import OPENAI_API_KEY

def extract_expense_details_with_date(user_input):
    """
    Extract expense details from natural language input using OpenAI, including date.
    
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
        
        # Extract expense details including date
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system", 
                    "content": "You are a financial assistant that categorizes expenses accurately and extracts dates."
                },
                {
                    "role": "user", 
                    "content": f"""Given this expense description: '{user_input}'
                    
                    1. Extract the numeric amount (if any)
                    2. Determine what this expense is for (transportation, food, etc.)
                    3. Create a brief description
                    4. Extract or infer the date of the expense (use today's date if not specified)
                    
                    Today's date is {datetime.datetime.now().strftime("%Y-%m-%d")}.
                    
                    Return ONLY a JSON with these fields:
                    - amount: the numeric value (without currency symbols)
                    - purpose: what general category this expense belongs to
                    - description: a brief description of the expense
                    - date: the date in YYYY-MM-DD format
                    
                    For example:
                    Input: "spent 50 on lunch today"
                    Output: {{"amount": 50, "purpose": "food", "description": "lunch", "date": "2025-04-08"}}
                    
                    Input: "100 for uber yesterday"
                    Output: {{"amount": 100, "purpose": "transportation", "description": "uber ride", "date": "2025-04-07"}}
                    
                    Input: "paid 25 for coffee on April 5"
                    Output: {{"amount": 25, "purpose": "food", "description": "coffee", "date": "2025-04-05"}}
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
def handle_multiple_expenses(user_input):
    """
    Handle multiple expenses entered in a single message.
    
    Args:
        user_input (str): User message containing multiple expenses
        
    Returns:
        str: Response message with results of processing all expenses
    """
    try:
        # Use OpenAI to split the input into separate expense statements
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        # First, determine if this is a multi-expense input and split it
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system", 
                    "content": "You are a financial assistant that helps identify and separate expense entries."
                },
                {
                    "role": "user", 
                    "content": f"""
                    The following text may contain one or more expense entries:
                    
                    "{user_input}"
                    
                    If there are multiple expense entries, separate them into distinct entries.
                    Return ONLY a JSON with an 'expenses' array, where each item is a separate expense entry.
                    
                    For example:
                    Input: "50 for lunch today and 20 for gas yesterday"
                    Output: {{"expenses": ["50 for lunch today", "20 for gas yesterday"]}}
                    
                    Input: "bought groceries 75, movie tickets 30, and coffee 5"
                    Output: {{"expenses": ["bought groceries 75", "movie tickets 30", "coffee 5"]}}
                    
                    If there's only one expense, still wrap it in an array.
                    Input: "paid 100 for dinner"
                    Output: {{"expenses": ["paid 100 for dinner"]}}
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
            return "I couldn't identify any expenses in your message. Please try again."
        
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
        
        # The rest of the function remains the same
        if len(results) == 1:
            return results[0]
        else:
            response = "I've processed your expenses:\n\n"
            for idx, result in enumerate(results, 1):
                response += f"{idx}. {result}\n"
            return response
    
    except Exception as e:
        return f"An error occurred while processing multiple expenses: {str(e)}"
        
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