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
        Also handles shared expenses (both 'they_owe_me' and 'i_owe_them' formats).
        
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
                shared_successes = []
                
                for expense_data in parsed_result:
                    # Check for parsing errors
                    if 'error' in expense_data:
                        failures.append(expense_data)
                        continue
                    
                    # Check if this is a shared expense
                    person = expense_data.get('person')
                    direction = expense_data.get('direction')
                    
                    # Log the expense to sheets
                    try:
                        # Always log as a regular expense
                        success = self.sheets.log_expense(expense_data)
                        
                        # If it's a shared expense, also log it to the Shared Expenses sheet
                        if person and direction and success:
                            self.sheets.log_shared_expense(expense_data)
                            shared_successes.append(expense_data)
                        
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
                    expense_details = []
                    for exp in successes:
                        person = exp.get('person')
                        direction = exp.get('direction')
                        
                        if person and direction:
                            if direction == 'they_owe_me':
                                shared_text = f" ({person} owes you)"
                            else:  # i_owe_them
                                shared_text = f" (you owe {person})"
                        else:
                            shared_text = ""
                        
                        expense_details.append(f"• {exp['amount']} for {exp['description']}{shared_text}")
                    
                    expense_list = "\n".join(expense_details)
                    return {
                        "success": True,
                        "message": f"Logged {len(successes)} expenses:\n{expense_list}",
                        "data": {
                            "successes": successes,
                            "failures": failures,
                            "shared_count": len(shared_successes),
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
                
                # Check if this is a shared expense
                person = expense_data.get('person')
                direction = expense_data.get('direction')
                
                # Log the expense to sheets
                success = self.sheets.log_expense(expense_data)
                
                # If it's a shared expense, also log it to the Shared Expenses sheet
                if person and direction and success:
                    self.sheets.log_shared_expense(expense_data)
                    if direction == 'they_owe_me':
                        shared_text = f" ({person} owes you)"
                    else:  # i_owe_them
                        shared_text = f" (you owe {person})"
                else:
                    shared_text = ""
                
                # Generate confirmation message
                return {
                    "success": success,
                    "message": f"Logged {expense_data['amount']} for {expense_data['description']}{shared_text}",
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
    
    def settle_debt(self, user_input):
        """
        Process a settlement request.
        
        Args:
            user_input (str): Natural language input describing the settlement
            
        Returns:
            dict: Result containing success status and message
        """
        try:
            # Extract person and amount from the input
            # Simple pattern: "settle [person] [amount]"
            parts = user_input.lower().replace("settle", "").strip().split()
            
            person = None
            amount = None
            
            # Try to identify person and amount
            for i, part in enumerate(parts):
                # Check if this part is a number (amount)
                try:
                    amt = float(part.replace(',', ''))
                    amount = amt
                    # Person is likely before the amount
                    if i > 0 and person is None:
                        person = parts[i-1]
                except ValueError:
                    # If not a number and we haven't found a person yet, this might be the person
                    if i == 0 or (person is None and i < len(parts) - 1):
                        person = part
            
            # If we still don't have a person, use the first word
            if person is None and parts:
                person = parts[0]
            
            # If still no person found, return error
            if not person:
                return {
                    "success": False,
                    "message": "Could not identify who to settle with. Please use format: settle [person] [amount]"
                }
            
            # Perform the settlement
            result = self.sheets.settle_shared_expense(person, amount)
            return result
            
        except Exception as e:
            if DEBUG:
                print(f"Error settling debt: {str(e)}")
            return {
                "success": False,
                "message": f"Error settling debt: {str(e)}",
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