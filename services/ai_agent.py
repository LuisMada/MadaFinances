"""
AI Agent Service
Central intelligence for the financial tracker, handling all language processing tasks.
"""
from openai import OpenAI
import json
import datetime
from config import OPENAI_API_KEY, OPENAI_MODEL, DEBUG

class AIAgent:
    def __init__(self):
        """Initialize the AI Agent with OpenAI client."""
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        
    def parse_debt(self, user_input):
        """
        Extract structured debt data from user input.
        
        Args:
            user_input (str): Natural language input from the user
            
        Returns:
            dict: Structured debt data dictionary
        """
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        
        try:
            completion = self.client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a financial assistant that extracts debt information from user messages."
                    },
                    {
                        "role": "user", 
                        "content": f"""Extract debt information from this message: '{user_input}'
                        
                        Return ONLY a JSON object with these fields:
                        - "date": in YYYY-MM-DD format (default to today: {today})
                        - "person": the name of the person involved in the debt (normalize to lowercase)
                        - "description": what the debt is for (can be empty if not mentioned)
                        - "amount": the monetary amount as a number (no currency symbols)
                        - "direction": either "to" (you owe them) or "from" (they owe you)
                        
                        IMPORTANT GUIDELINES:
                        
                        1. MOST IMPORTANT PATTERN: If text is inside parentheses, it's a person's name
                           - Look for a pattern: "<amount> <description> (<person_name>)"
                           - For example: "200 hotdog (john)" means john owes me 200 for hotdog
                           - For example: "500 dinner (jana)" means jana owes me 500 for dinner
                           - ALWAYS set direction to "from" when a name is in parentheses (they owe the user)
                           
                        2. If a dash precedes a word, it's a person's name and it means the user owes them
                           - Look for pattern: "<amount> <description> - <person_name>"
                           - For example: "200 lunch - mary" means I owe mary 200 for lunch
                           - ALWAYS set direction to "to" when a name follows a dash (user owes them)
                        
                        3. Make sure to accurately extract:
                           - The correct person name (even if it's a unique or uncommon name)
                           - The correct amount as a number
                           - The correct description of what the debt is for
                           
                        4. By default, if no clear direction can be determined:
                           - If a person name is in parentheses, they owe the user (direction="from")
                           - If a person name follows a dash, the user owes them (direction="to")
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
            parsed_data = json.loads(content)
            
            if DEBUG:
                print(f"Parsed debt data: {parsed_data}")
            
            return parsed_data
            
        except Exception as e:
            print(f"Error parsing debt: {str(e)}")
            # Return default structure for error handling
            return {
                "date": today,
                "person": "",
                "description": user_input,
                "amount": 0,
                "direction": "from",
                "error": str(e)
            }
    
    def parse_debt_settlement(self, user_input):
        """
        Extract structured settlement data from user input.
        
        Args:
            user_input (str): Natural language input from the user
            
        Returns:
            dict: Structured settlement data dictionary
        """
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        
        try:
            # First try direct pattern matching for "settle [person] [amount]"
            import re
            settle_pattern = re.search(r'settle\s+(\w+)\s+(\d+)', user_input.lower())
            if settle_pattern:
                person = settle_pattern.group(1)
                amount = float(settle_pattern.group(2))
                
                if DEBUG:
                    print(f"Direct pattern match: settling with {person} for {amount}")
                
                return {
                    "date": today,
                    "person": person.lower(),
                    "amount": amount
                    # Don't specify direction - we'll check all debts with this person regardless of direction
                }
            
            # If no direct pattern match, use AI
            completion = self.client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a financial assistant that extracts debt settlement information from user messages."
                    },
                    {
                        "role": "user", 
                        "content": f"""Extract debt settlement information from this message: '{user_input}'
                        
                        Return ONLY a JSON object with these fields:
                        - "date": in YYYY-MM-DD format (default to today: {today})
                        - "person": the name of the person involved in the settlement (normalize to lowercase)
                        - "amount": the monetary amount as a number (no currency symbols)
                        
                        IMPORTANT GUIDELINES:
                        1. Focus on extracting:
                           - The correct person name who is involved in the settlement
                           - The monetary amount being settled
                           - The date if specified (default to today)
                        
                        2. For simple settlement messages like:
                           - "settle john 100"
                           - "settle 200 with mary"
                           - "pay sara 150"
                           
                        Just extract the person and amount - we'll determine the direction later.
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
            parsed_data = json.loads(content)
            
            if DEBUG:
                print(f"Parsed settlement data: {parsed_data}")
            
            return parsed_data
            
        except Exception as e:
            print(f"Error parsing settlement: {str(e)}")
            # Return default structure for error handling
            return {
                "date": today,
                "person": "",
                "amount": None,
                "error": str(e)
            }

    def detect_intent(self, user_input):
        """
        Detect the user's intent from their natural language input.
        Updated to support debt tracking functionality with parentheses syntax.
        
        Args:
            user_input (str): Natural language input from the user
            
        Returns:
            dict: Dictionary containing intent type and relevant data
        """
        try:
            # Use chat completions API with improved prompt
            completion = self.client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a financial assistant that categorizes user messages into clear intents. Your primary purpose is to distinguish between expense entries, debt tracking, and other requests."
                    },
                    {
                        "role": "user", 
                        "content": f"""Classify this message: '{user_input}'. 
                        Return ONLY a JSON with 'intent' and 'data'.
                        
                        Intents are strictly one of:
                        - "expense" (user is logging a personal expense)
                        - "summary" (user wants to see a summary of expenses)
                        - "budget_status" (user wants to check their budget status)
                        - "set_budget" (user wants to set or update a budget)
                        - "delete_expense" (user wants to delete an expense)
                        - "help" (user needs help)
                        - "debt_add" (user is recording money owed to/from someone)
                        - "debt_settle" (user is settling a debt with someone)
                        - "debt_balance" (user wants to check debt balance with someone)
                        - "other" (anything else)
                        
                        IMPORTANT GUIDELINES:
                        1. MOST IMPORTANT: Look for parentheses pattern first! If the message contains anything in parentheses ( ), assume it's a person name and classify as "debt_add"
                           Examples: 
                           - "200 hotdog (john)" → debt_add
                           - "500 dinner (jana)" → debt_add
                           - "10 coffee (alice)" → debt_add
                           - ANY amount followed by text and then (any_name) → debt_add
                        
                        2. If the message has a dash before a word, it's likely a person name, classify as "debt_add"
                           Examples:
                           - "200 lunch - mary" → debt_add
                           - "50 tickets - bob" → debt_add
                        
                        3. If parentheses or dash patterns are not found:
                           - If the message contains a product/service name and an amount without any person mentioned, classify as "expense"
                           - If the message mentions money owed by or to a specific person, classify as "debt_add"
                           - If the message mentions settling, paying, or clearing a debt with someone, classify as "debt_settle"
                           - If the message asks about balance, what someone owes, or what is owed to someone, classify as "debt_balance"
                        
                        4. For debt intents, include relevant information in the data field:
                           - For "debt_add", include 'person', 'amount', and 'direction' ('to' or 'from') if detectable
                           - For "debt_settle", include 'person' and 'amount' if mentioned
                           - For "debt_balance", include 'person' if a specific person is mentioned
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
            
            if DEBUG:
                print(f"Intent detected: {intent_data}")
                
            return intent_data
            
        except Exception as e:
            print(f"Error detecting intent: {str(e)}")
            # Return a default intent for error handling
            return {"intent": "error", "data": {"message": str(e)}}
    
    def parse_expense(self, user_input, categories, current_date=None):
        """
        Extract structured expense data from user input.
        Supports parsing multiple expenses from a single message.
        
        Args:
            user_input (str): Natural language input from the user
            categories (list): List of available expense categories
            current_date (str, optional): Current date in YYYY-MM-DD format
            
        Returns:
            list: List of structured expense data dictionaries, or single dict if only one expense
        """
        # Use provided date or get current date
        today = current_date if current_date else datetime.datetime.now().strftime("%Y-%m-%d")
        
        try:
            completion = self.client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a financial assistant that extracts expense information from user messages."
                    },
                    {
                        "role": "user", 
                        "content": f"""Extract expense information from this message: '{user_input}'
                        
                        If there is only ONE expense, return a JSON object with these fields:
                        - "date": in YYYY-MM-DD format (default to today: {today})
                        - "description": a clear description of the expense
                        - "amount": the monetary amount as a number (no currency symbols)
                        - "category": the best matching category from this list: {', '.join(categories)}
                        - "multiple": false
                        
                        If there are MULTIPLE expenses, return a JSON with:
                        - "multiple": true
                        - "expenses": an array where each item contains the fields above (without the "multiple" field)
                        """
                    }
                ],
                temperature=0  # Low temperature for consistent parsing
            )
            
            # Get the response content
            content = completion.choices[0].message.content
            
            # Clean the content if needed
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].strip()
                
            # Parse JSON
            parsed_data = json.loads(content)
            
            if DEBUG:
                print(f"AI parsed result: {parsed_data}")
            
            # Check if we have multiple expenses
            if parsed_data.get("multiple", False):
                # Process each expense in the list
                expenses = []
                for exp in parsed_data.get("expenses", []):
                    # Add source to each expense
                    exp["source"] = "telegram"
                    expenses.append(exp)
                
                if DEBUG:
                    print(f"Parsed multiple expenses: {expenses}")
                
                return expenses
            else:
                # Single expense
                # Remove the 'multiple' field
                if "multiple" in parsed_data:
                    del parsed_data["multiple"]
                
                # Add source
                parsed_data["source"] = "telegram"
                
                if DEBUG:
                    print(f"Parsed single expense: {parsed_data}")
                
                return parsed_data
            
        except Exception as e:
            print(f"Error parsing expense: {str(e)}")
            # Return default structure for error handling
            return {
                "date": today,
                "description": user_input,
                "amount": 0,
                "category": "Other",
                "source": "telegram",
                "error": str(e)
            }
    
    def analyze_budget(self, budget_data, expenses):
        """
        Analyze budget status based on expenses and budget data.
        Updated to handle custom period budgets.
        
        Args:
            budget_data (dict): Budget information
            expenses (list): List of expense dictionaries
            
        Returns:
            dict: Budget analysis with insights
        """
        try:
            expenses_json = json.dumps(expenses[:20])  # Limit for prompt size
            budget_json = json.dumps(budget_data)
            
            completion = self.client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a financial assistant that analyzes budget performance against actual spending."
                    },
                    {
                        "role": "user", 
                        "content": f"""Analyze the following budget performance:
                        
                        Budget data:
                        {budget_json}
                        
                        Expense data (sample):
                        {expenses_json}
                        
                        GUIDELINES:
                        1. Return ONLY a JSON with these fields:
                        - "status": "under_budget", "near_limit", or "over_budget"
                        - "message": A helpful insight about the budget situation
                        - "percentage_used": Percentage of budget used (0-100+)
                        - "remaining": Amount remaining in the budget (can be negative)
                        - "daily_budget": Budget amount per day
                        - "daily_average": Average daily spending
                        - "days_elapsed": Number of days elapsed in the budget period
                        - "days_remaining": Number of days remaining in the budget period
                        - "remaining_daily_allowance": Remaining budget divided by remaining days
                        
                        2. Consider:
                        - If a category budget exists, analyze only that category
                        - Otherwise, analyze total spending against total budget
                        - Use "near_limit" status when within 10% of the budget limit
                        - For custom periods, calculate daily allowance based on the budget and period length
                        - For daily calculations, use the actual number of days in the period (7 for weekly, specified days for custom)
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
            analysis = json.loads(content)
            
            if DEBUG:
                print(f"Budget analysis: {analysis}")
                
            return analysis
            
        except Exception as e:
            print(f"Error analyzing budget: {str(e)}")
            # Return default analysis for error handling
            return {
                "status": "unknown",
                "message": f"Unable to analyze budget: {str(e)}",
                "percentage_used": 0,
                "remaining": 0,
                "daily_budget": 0,
                "daily_average": 0,
                "days_elapsed": 0,
                "days_remaining": 0,
                "remaining_daily_allowance": 0
            }
    
    def parse_budget_request(self, user_input, categories):
        """
        Parse a budget setting request from user input, including custom periods.
        
        Args:
            user_input (str): Natural language input from the user
            categories (list): List of available expense categories
            
        Returns:
            dict: Structured budget data including amount, period, category, days
        """
        try:
            completion = self.client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a financial assistant that extracts budget setting information from user messages, including custom periods."
                    },
                    {
                        "role": "user", 
                        "content": f"""Extract budget setting information from: '{user_input}'
                        
                        Return ONLY a JSON with these fields:
                        - "amount": the budget amount as a number (no currency symbols)
                        - "period": either "weekly", "monthly", or "custom"
                        - "days": if a custom period is mentioned, extract the number of days (integer)
                        - "category": the best matching category from this list: {', '.join(categories)}, or "all" for overall budget
                        - "start_date": start date in YYYY-MM-DD format (default to today if not specified)
                        
                        IMPORTANT GUIDELINES:
                        1. Default to "monthly" period if not clearly specified
                        2. Default to "all" for category if not specified
                        3. If amount appears to be numeric with a currency symbol, just extract the number
                        4. Set period to "custom" if the user specifies a number of days (e.g., "next 10 days", "5 days")
                        5. For custom periods, populate the "days" field with the number of days
                        
                        Examples:
                        - "set my food budget to 300" -> {"amount": 300, "period": "monthly", "category": "Food", "start_date": "today"}
                        - "weekly spending limit 200" -> {"amount": 200, "period": "weekly", "category": "all", "start_date": "today"}
                        - "set 150 budget for next 5 days" -> {"amount": 150, "period": "custom", "days": 5, "category": "all", "start_date": "today"}
                        - "budget of 300 for the next 10 days for food" -> {"amount": 300, "period": "custom", "days": 10, "category": "Food", "start_date": "today"}
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
            budget_data = json.loads(content)
            
            # Add active flag
            budget_data["active"] = True
            
            # Ensure days field exists
            if "days" not in budget_data and budget_data["period"] == "custom":
                budget_data["days"] = 30  # Default fallback
            elif "days" not in budget_data:
                # Set days based on period for consistency
                if budget_data["period"] == "weekly":
                    budget_data["days"] = 7
                else:  # monthly
                    budget_data["days"] = 30
            
            if DEBUG:
                print(f"Parsed budget request: {budget_data}")
                
            return budget_data
            
        except Exception as e:
            print(f"Error parsing budget request: {str(e)}")
            # Return default structure for error handling
            return {
                "amount": 0,
                "period": "monthly",
                "days": 30,  # Default to 30 days
                "category": "all",
                "start_date": datetime.datetime.now().strftime("%Y-%m-%d"),
                "active": True,
                "error": str(e)
            }