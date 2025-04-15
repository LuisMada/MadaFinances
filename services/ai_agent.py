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
        
    def detect_intent(self, user_input):
        """
        Detect the user's intent from their natural language input.
        Updated to support custom period budgets.
        
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
                        - "delete_expense" (user wants to delete an expense)
                        - "help" (user needs help)
                        - "other" (anything else)
                        
                        IMPORTANT GUIDELINES:
                        1. If the message contains a product/service name and an amount, classify as "expense"
                        2. If the message is very short with just an item and a number, it's an "expense"
                        3. Words like "summary", "report", "show me" suggest a "summary" intent
                        4. Budget-related words like "budget", "spending limit" suggest "budget_status" or "set_budget"
                        5. Words like "delete", "remove", "erase" suggest a "delete_expense" intent
                        6. Messages about "setting budget for next X days" are "set_budget" intent
                        7. Messages asking about "how much is left in my budget" are "budget_status" intent
                        
                        Examples of "set_budget" intent with custom periods:
                        - "set 200 budget for next 5 days" -> set_budget
                        - "create a budget of 500 for the next 14 days" -> set_budget
                        
                        Examples of "budget_status" for custom periods:
                        - "how much do I have left in my 5-day budget" -> budget_status
                        - "check my custom period budget" -> budget_status
                        
                        For "expense" intent, include 'amount' and 'description' in data if possible.
                        For "summary" intent, include 'period' (e.g., 'this week', 'last month') in data.
                        For "set_budget", include 'amount', 'category' (if mentioned), 'period' ('weekly', 'monthly', or 'custom'), and 'days' (if custom period) in data.
                        For "delete_expense", include any identifiable information like 'description' or 'date' in data.
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
    
    def parse_expense(self, user_input, categories):
        """
        Extract structured expense data from user input.
        Supports parsing multiple expenses from a single message.
        Detects both directions of shared expenses:
        - 'paid for someone' format using parentheses: "50 lunch (Jane)" - they owe me
        - 'I owe someone' format using dash: "50 lunch - Jane" - I owe them
        
        Args:
            user_input (str): Natural language input from the user
            categories (list): List of available expense categories
            
        Returns:
            list: List of structured expense data dictionaries, or single dict if only one expense
        """
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        
        try:
            completion = self.client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a financial assistant that extracts expense information from user messages. You analyze the exact format and semantics to determine shared expense relationships accurately."
                    },
                    {
                        "role": "user", 
                        "content": f"""Extract expense information from this message: '{user_input}'
                        
                        IMPORTANT: Pay special attention to shared expense formats:
                        1. Format "X (Person)" means Person owes the user (direction: "they_owe_me")
                        2. Format "X - Person" means the user owes Person (direction: "i_owe_them")
                        
                        Examples for clarity:
                        - "50 lunch (Jane)" → Person: Jane, Direction: they_owe_me
                        - "50 lunch - Jane" → Person: Jane, Direction: i_owe_them
                        
                        If there is only ONE expense, return a JSON object with these fields:
                        - "date": in YYYY-MM-DD format (default to today: {today})
                        - "description": a clear description of the expense
                        - "amount": the monetary amount as a number (no currency symbols)
                        - "category": the best matching category from this list: {', '.join(categories)}
                        - "multiple": false
                        - "person": if shared expense, the name of the other person, otherwise null
                        - "direction": if shared expense, either "they_owe_me" or "i_owe_them", otherwise null
                        
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
                "person": None,
                "direction": None,
                "error": str(e)
            }
                
            except Exception as e:
                print(f"Error parsing expense: {str(e)}")
                # Return default structure for error handling
                return {
                    "date": today,
                    "description": user_input,
                    "amount": 0,
                    "category": "Other",
                    "source": "telegram",
                    "person": None,
                    "direction": None,
                    "error": str(e)
                }
    
    def generate_summary(self, expenses, period=None, budget_data=None):
        """
        Generate a natural language summary of expenses.
        
        Args:
            expenses (list): List of expense dictionaries
            period (str, optional): Time period for the summary
            budget_data (dict, optional): Budget information to include in the summary
            
        Returns:
            str: Natural language summary of expenses
        """
        try:
            # Calculate some basic statistics
            total_spent = sum(float(exp.get('Amount', 0)) for exp in expenses)
            category_totals = {}
            
            for expense in expenses:
                category = expense.get('Category', 'Other')
                amount = float(expense.get('Amount', 0))
                
                if category in category_totals:
                    category_totals[category] += amount
                else:
                    category_totals[category] = amount
            
            # Sort categories by amount spent
            sorted_categories = sorted(
                category_totals.items(), 
                key=lambda x: x[1], 
                reverse=True
            )
            
            # Prepare data for the AI
            expenses_json = json.dumps(expenses[:10])  # Limit to first 10 for prompt size
            categories_json = json.dumps(sorted_categories)
            
            completion = self.client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a financial assistant that creates concise, insightful summaries of spending patterns."
                    },
                    {
                        "role": "user", 
                        "content": f"""Create a spending summary for {period if period else 'recent expenses'}.
                        
                        Expense data (sample):
                        {expenses_json}
                        
                        Total spent: {total_spent}
                        
                        Spending by category:
                        {categories_json}
                        
                        {f'Budget information: {json.dumps(budget_data)}' if budget_data else ''}
                        
                        GUIDELINES:
                        1. Create a concise, conversational summary of spending patterns
                        2. Highlight top spending categories and any unusual expenses
                        3. If budget data is available, mention how spending compares to budget
                        4. Include the total amount spent
                        5. Keep your response under 250 words
                        """
                    }
                ],
                temperature=0.7  # Slightly higher temperature for more natural language
            )
            
            # Get the response content
            summary = completion.choices[0].message.content
            
            if DEBUG:
                print(f"Generated summary: {summary}")
                
            return summary
            
        except Exception as e:
            print(f"Error generating summary: {str(e)}")
            # Return a basic summary for error handling
            return f"Summary for {period if period else 'recent expenses'}: Total spent: {sum(float(exp.get('Amount', 0)) for exp in expenses)}. Error: {str(e)}"
    
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