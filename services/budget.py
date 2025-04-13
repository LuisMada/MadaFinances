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