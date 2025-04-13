"""
Summary Service
Generates financial summaries and reports.
"""
import datetime
from .ai_agent import AIAgent
from .sheets import SheetsService
from config import DEBUG

class SummaryService:
    def __init__(self):
        """Initialize the Summary Service."""
        self.ai = AIAgent()
        self.sheets = SheetsService()
    
    def generate_summary(self, user_input):
        """
        Generate a summary of expenses based on user input.
        
        Args:
            user_input (str): Natural language input from the user (containing period info)
            
        Returns:
            dict: Result containing success status and message
        """
        try:
            # Extract period information from user input
            period = self._extract_period(user_input)
            
            # Calculate date range based on period
            start_date, end_date = self._get_date_range_from_period(period)
            
            # Get expenses for the date range
            expenses = self.sheets.get_expenses_in_date_range(
                start_date=start_date,
                end_date=end_date
            )
            
            if not expenses:
                return {
                    "success": True,
                    "message": f"No expenses found for {period if period else 'recent period'}",
                    "data": {"period": period, "expenses": []}
                }
            
            # Determine budget period type based on the summary period
            budget_period = "monthly"
            if period in ["today", "yesterday", "this_week", "last_week"]:
                budget_period = "weekly"
            
            # Get any relevant budget data
            budget_data = self.sheets.get_budget(period=budget_period)
            
            # Generate the summary using AI
            summary = self.ai.generate_summary(expenses, period, budget_data)
            
            return {
                "success": True,
                "message": summary,
                "data": {
                    "period": period,
                    "expense_count": len(expenses),
                    "budget": budget_data
                }
            }
            
        except Exception as e:
            if DEBUG:
                print(f"Error generating summary: {str(e)}")
            return {
                "success": False,
                "message": f"Error generating summary: {str(e)}",
                "data": {}
            }
    
    def _extract_period(self, user_input):
        """
        Extract time period from user input.
        This is a simple keyword-based extraction, could be enhanced with AI.
        
        Args:
            user_input (str): User's message
            
        Returns:
            str: Period identifier ('today', 'this_week', 'this_month', 'last_month', etc.)
        """
        user_input = user_input.lower()
        
        if "today" in user_input:
            return "today"
        elif "yesterday" in user_input:
            return "yesterday"
        elif "this week" in user_input:
            return "this_week"
        elif "last week" in user_input:
            return "last_week"
        elif "this month" in user_input:
            return "this_month"
        elif "last month" in user_input:
            return "last_month"
        elif "year" in user_input:
            if "this" in user_input:
                return "this_year"
            elif "last" in user_input:
                return "last_year"
        
        # Default to this month if no specific period mentioned
        return "this_month"
    
    def _get_date_range_from_period(self, period):
        """
        Convert a period identifier to a date range.
        
        Args:
            period (str): Period identifier ('today', 'this_week', 'this_month', etc.)
            
        Returns:
            tuple: (start_date, end_date) as datetime.date objects
        """
        today = datetime.date.today()
        
        if period == "today":
            return today, today
        
        elif period == "yesterday":
            yesterday = today - datetime.timedelta(days=1)
            return yesterday, yesterday
        
        elif period == "this_week":
            # Start of week (Monday)
            start_of_week = today - datetime.timedelta(days=today.weekday())
            return start_of_week, today
        
        elif period == "last_week":
            # Last week's Monday and Sunday
            this_week_start = today - datetime.timedelta(days=today.weekday())
            last_week_start = this_week_start - datetime.timedelta(days=7)
            last_week_end = this_week_start - datetime.timedelta(days=1)
            return last_week_start, last_week_end
        
        elif period == "this_month":
            # Start of month
            start_of_month = today.replace(day=1)
            return start_of_month, today
        
        elif period == "last_month":
            # First and last day of previous month
            first_of_month = today.replace(day=1)
            last_month_end = first_of_month - datetime.timedelta(days=1)
            last_month_start = last_month_end.replace(day=1)
            return last_month_start, last_month_end
        
        elif period == "this_year":
            # Start of year
            start_of_year = today.replace(month=1, day=1)
            return start_of_year, today
        
        elif period == "last_year":
            # Last year's range
            last_year = today.year - 1
            start_date = datetime.date(last_year, 1, 1)
            end_date = datetime.date(last_year, 12, 31)
            return start_date, end_date
        
        # Default to this month
        start_of_month = today.replace(day=1)
        return start_of_month, today