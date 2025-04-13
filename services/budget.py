"""
Updated Budget Service
Handles budget setting and analysis, including custom period budgets.
"""
import datetime
import traceback
from .ai_agent import AIAgent
from .sheets import SheetsService
from config import DEBUG, BUDGETS_SHEET

class BudgetService:
    def __init__(self):
        """Initialize the Budget Service."""
        self.ai = AIAgent()
        self.sheets = SheetsService()
    
    def set_budget(self, budget_data):
        """
        Create or update a budget, including custom periods.
        
        Args:
            budget_data (dict): Dictionary containing budget details
                Required keys: amount, period, category, start_date, active
                Optional keys: days (for custom periods)
        
        Returns:
            bool: True if successful
        """
        try:
            if DEBUG:
                print(f"Setting budget in Google Sheets: {budget_data}")
            
            # Parse the budget data using AI if it's a string
            if isinstance(budget_data, str):
                # Get available categories
                categories = self.sheets.get_categories()
                budget_data = self.ai.parse_budget_request(budget_data, categories)
            
            # Call the sheets service to set the budget
            success = self.sheets.set_budget(budget_data)
            
            if success:
                return {
                    "success": True,
                    "message": f"Budget set: {budget_data['amount']} for {budget_data['period']} period",
                    "data": budget_data
                }
            else:
                return {
                    "success": False,
                    "message": "Failed to set budget",
                    "data": budget_data
                }
            
        except Exception as e:
            if DEBUG:
                print(f"Error setting budget: {str(e)}")
                traceback.print_exc()
            return {
                "success": False,
                "message": f"Error setting budget: {str(e)}",
                "data": {}
            }
    
    """
    Budget status method for BudgetService
    Add this method to your BudgetService class in budget.py
    """

    def get_budget_status(self, user_input=None):
        """
        Get current budget status with minimal processing.
        
        Args:
            user_input (str, optional): Not used in simplified version
            
        Returns:
            dict: Result with budget status
        """
        try:
            # Get any active budget (simplified to just get the latest one)
            budget = self.sheets.get_budget()
            
            if not budget:
                return {
                    "success": False,
                    "message": "No active budget found. Set a budget first.",
                    "data": {}
                }
            
            # Get expenses for the budget period
            start_date = self._date_from_str(budget.get('StartDate', datetime.datetime.now().strftime("%Y-%m-%d")))
            end_date = datetime.datetime.now().date()
            
            category = budget.get('Category', 'all')
            if category.lower() == 'all':
                category = None  # Don't filter by category if it's "all"
                
            expenses = self.sheets.get_expenses_in_date_range(
                start_date=start_date,
                end_date=end_date,
                category=category
            )
            
            # Calculate total spent
            total_spent = sum(float(exp.get('Amount', 0)) for exp in expenses)
            
            # Get budget amount
            budget_amount = float(budget.get('Amount', 0))
            
            # Calculate remaining budget
            remaining = budget_amount - total_spent
            
            # Calculate percentage used
            percentage_used = (total_spent / budget_amount * 100) if budget_amount > 0 else 0
            
            # Determine status
            if percentage_used >= 100:
                status = "over_budget"
                status_message = "You've exceeded your budget."
            elif percentage_used >= 90:
                status = "near_limit"
                status_message = "You're close to your budget limit."
            else:
                status = "under_budget"
                status_message = "You're under budget."
            
            # Calculate days info for custom periods
            days_total = int(budget.get('Days', 30))
            days_elapsed = (datetime.datetime.now().date() - start_date).days + 1
            days_remaining = max(0, days_total - days_elapsed)
            
            daily_budget = budget_amount / days_total if days_total > 0 else 0
            daily_average = total_spent / days_elapsed if days_elapsed > 0 else 0
            
            remaining_daily = remaining / days_remaining if days_remaining > 0 else 0
            
            result = {
                "success": True,
                "message": status_message,
                "data": {
                    "budget_amount": budget_amount,
                    "total_spent": total_spent,
                    "remaining": remaining,
                    "percentage_used": percentage_used,
                    "status": status,
                    "period": budget.get('Period', 'custom'),
                    "days_total": days_total,
                    "days_elapsed": days_elapsed,
                    "days_remaining": days_remaining,
                    "daily_budget": daily_budget,
                    "daily_average": daily_average,
                    "remaining_daily": remaining_daily,
                    "category": budget.get('Category', 'all')
                }
            }
            
            return result
            
        except Exception as e:
            if DEBUG:
                print(f"Error getting budget status: {str(e)}")
            return {
                "success": False,
                "message": f"Error getting budget status: {str(e)}",
                "data": {}
            }

    def _date_from_str(self, date_str):
        """Convert string date to datetime.date object."""
        try:
            return datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        except:
            # Return today's date as fallback
            return datetime.datetime.now().date()
    
    def get_budget(self, category=None, period=None):
        """
        Get current budget status.
        
        Args:
            category (str, optional): Category to filter by
            period (str, optional): Period to filter by ('weekly', 'monthly', 'custom')
        
        Returns:
            dict: Budget information
        """
        try:
            # Select the "Budgets" worksheet
            worksheet = self.spreadsheet.worksheet(BUDGETS_SHEET)
            
            # Get all values including headers
            all_values = worksheet.get_all_values()
            
            # Check if there's data (should be at least headers)
            if len(all_values) <= 1:
                return None
                
            # Extract headers and data
            headers = all_values[0]
            data = all_values[1:]
            
            # Debug log to see what's in the budget sheet
            if DEBUG:
                print(f"Budget headers: {headers}")
                print(f"Budget data (first 5 rows): {data[:5] if len(data) >= 5 else data}")
            
            # Convert to list of dictionaries
            budgets = []
            for row in data:
                # Make sure we have complete rows
                if len(row) < len(headers):
                    # Skip incomplete rows
                    continue
                    
                budget = dict(zip(headers, row))
                budgets.append(budget)
            
            # Debug log to see how many budgets were found
            if DEBUG:
                print(f"Found {len(budgets)} total budgets")
            
            # Filter active budgets (check both 'True' and 'TRUE' for case-insensitive comparison)
            active_budgets = [b for b in budgets if b.get('Active', '').lower() == 'true']
            
            if DEBUG:
                print(f"Found {len(active_budgets)} active budgets")
            
            # Apply category filter if provided
            if category and category.lower() != 'all':
                filtered_budgets = [b for b in active_budgets if b.get('Category', '').lower() == category.lower()]
                # If no specific category budget, look for 'all' category
                if not filtered_budgets:
                    filtered_budgets = [b for b in active_budgets if b.get('Category', '').lower() == 'all']
            else:
                # Look for 'all' category budget first
                filtered_budgets = [b for b in active_budgets if b.get('Category', '').lower() == 'all']
                # If no 'all' category budget, return any active budget
                if not filtered_budgets:
                    filtered_budgets = active_budgets
            
            # Debug log after category filtering
            if DEBUG:
                print(f"Found {len(filtered_budgets)} budgets after category filtering")
            
            # Apply period filter if provided
            if period:
                period_budgets = [b for b in filtered_budgets if b.get('Period', '').lower() == period.lower()]
                # Only use period filtering if it yields results
                if period_budgets:
                    filtered_budgets = period_budgets
                    
            # Debug log after period filtering
            if DEBUG:
                print(f"Found {len(filtered_budgets)} budgets after period filtering")
            
            # Return the most recent budget if multiple found
            if filtered_budgets:
                # Sort by start date (most recent first)
                sorted_budgets = sorted(
                    filtered_budgets,
                    key=lambda x: self._date_from_str(x.get('StartDate', '1970-01-01')),
                    reverse=True
                )
                return sorted_budgets[0]
            
            return None
            
        except Exception as e:
            print(f"Error retrieving budget: {str(e)}")
            traceback.print_exc()
            return None