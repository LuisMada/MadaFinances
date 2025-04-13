"""
Expense Service
Handles expense logging and management.
"""
from .ai_agent import AIAgent
from .sheets import SheetsService
from config import DEBUG

class ExpenseService:
    def __init__(self):
        """Initialize the Expense Service."""
        self.ai = AIAgent()
        self.sheets = SheetsService()
    
    def process_expense(self, user_input):
        """
        Process a user's expense entry.
        Supports processing multiple expenses from a single message.
        
        Args:
            user_input (str): Natural language input from the user
            
        Returns:
            dict: Result containing success status and message
        """
        try:
            # Get available categories
            categories = self.sheets.get_categories()
            
            # Parse the expense(s) using AI
            parsed_result = self.ai.parse_expense(user_input, categories)
            
            # Check if we have multiple expenses or a single one
            if isinstance(parsed_result, list):
                # Multiple expenses
                successes = []
                failures = []
                
                for expense_data in parsed_result:
                    # Check for parsing errors
                    if 'error' in expense_data:
                        failures.append(expense_data)
                        continue
                    
                    # Log the expense to sheets
                    try:
                        success = self.sheets.log_expense(expense_data)
                        if success:
                            successes.append(expense_data)
                        else:
                            failures.append(expense_data)
                    except Exception as e:
                        failures.append(expense_data)
                        if DEBUG:
                            print(f"Error logging expense: {str(e)}")
                
                # Generate confirmation message
                if len(successes) > 0:
                    # Format success message for multiple expenses
                    expense_details = "\n".join([f"• {exp['amount']} for {exp['description']}" for exp in successes])
                    return {
                        "success": True,
                        "message": f"Logged {len(successes)} expenses:\n{expense_details}",
                        "data": {
                            "successes": successes,
                            "failures": failures,
                            "multiple": True
                        }
                    }
                else:
                    return {
                        "success": False,
                        "message": "Failed to log expenses",
                        "data": {
                            "failures": failures,
                            "multiple": True
                        }
                    }
            else:
                # Single expense
                expense_data = parsed_result
                
                # Check for parsing errors
                if 'error' in expense_data:
                    return {
                        "success": False,
                        "message": f"Error parsing expense: {expense_data['error']}",
                        "data": expense_data
                    }
                
                # Log the expense to sheets
                success = self.sheets.log_expense(expense_data)
                
                # Generate confirmation message
                return {
                    "success": success,
                    "message": f"Logged {expense_data['amount']} for {expense_data['description']}",
                    "data": expense_data
                }
            
        except Exception as e:
            if DEBUG:
                print(f"Error processing expense: {str(e)}")
            return {
                "success": False,
                "message": f"Error processing expense: {str(e)}",
                "data": {}
            }
    
    def delete_expense(self, user_input):
        """
        Delete an expense based on user description.
        
        Args:
            user_input (str): Description of the expense to delete
            
        Returns:
            dict: Result containing success status and message
        """
        try:
            # Extract key identifier from user input
            # This is a simple approach, we could use AI for more complex matching
            identifier = user_input.lower().replace("delete", "").replace("remove", "").strip()
            
            # Delete the expense
            success = self.sheets.delete_expense(identifier)
            
            if success:
                return {
                    "success": True,
                    "message": f"Successfully deleted expense matching '{identifier}'",
                    "data": {"identifier": identifier}
                }
            else:
                return {
                    "success": False,
                    "message": f"No expenses found matching '{identifier}'",
                    "data": {"identifier": identifier}
                }
                
        except Exception as e:
            if DEBUG:
                print(f"Error deleting expense: {str(e)}")
            return {
                "success": False,
                "message": f"Error deleting expense: {str(e)}",
                "data": {}
            }