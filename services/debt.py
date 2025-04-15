"""
Debt Service
Handles debt recording, settlement, and balance reporting.
"""
import datetime
import uuid
from .ai_agent import AIAgent
from .sheets import SheetsService
from config import DEBUG

class DebtService:
    def __init__(self):
        """Initialize the Debt Service."""
        self.ai = AIAgent()
        self.sheets = SheetsService()
    
    def add_debt(self, user_input):
        """
        Process a user's debt entry.
        
        Args:
            user_input (str): Natural language input from the user
            
        Returns:
            dict: Result containing success status and message
        """
        try:
            # Parse the debt using AI (to be implemented in AIAgent)
            debt_data = self.ai.parse_debt(user_input)
            
            # Check for parsing errors
            if 'error' in debt_data:
                return {
                    "success": False,
                    "message": f"Error parsing debt: {debt_data['error']}",
                    "data": debt_data
                }
            
            # Add auto-generated fields
            debt_data["id"] = str(uuid.uuid4())
            debt_data["status"] = "active"
            
            # Ensure date is set
            if "date" not in debt_data:
                debt_data["date"] = datetime.datetime.now().strftime("%Y-%m-%d")
            
            # Record the debt to sheets
            success = self.sheets.record_debt(debt_data)
            
            # Generate confirmation message
            if success:
                # Format different messages based on direction
                if debt_data["direction"] == "from":  # They owe you
                    message = f"✅ Recorded: {debt_data['person']} owes you {debt_data['amount']}"
                    if debt_data.get("description"):
                        message += f" for {debt_data['description']}"
                else:  # You owe them
                    message = f"✅ Recorded: You owe {debt_data['person']} {debt_data['amount']}"
                    if debt_data.get("description"):
                        message += f" for {debt_data['description']}"
                
                return {
                    "success": True,
                    "message": message,
                    "data": debt_data
                }
            else:
                return {
                    "success": False,
                    "message": "Failed to record debt",
                    "data": debt_data
                }
                
        except Exception as e:
            if DEBUG:
                print(f"Error adding debt: {str(e)}")
            return {
                "success": False,
                "message": f"Error adding debt: {str(e)}",
                "data": {}
            }
    
    def get_balance(self, person=None):
        """
        Get the balance with a specific person or all balances.
        
        Args:
            person (str, optional): Person to get balance for. If None, returns all balances.
            
        Returns:
            dict: Result containing success status and message
        """
        try:
            if person:
                # Get balance for specific person
                balance = self.sheets.get_net_balance(person)
                
                if not balance:
                    return {
                        "success": True,
                        "message": f"No active debts with {person}",
                        "data": {"person": person, "balance": 0}
                    }
                
                # Format message based on balance direction
                if balance["balance"] == 0:
                    message = f"You and {balance['person']} are all square! No debts between you."
                elif balance["they_owe"]:
                    message = f"{balance['person']} owes you {balance['amount']}"
                else:
                    message = f"You owe {balance['person']} {balance['amount']}"
                
                return {
                    "success": True,
                    "message": message,
                    "data": balance
                }
            else:
                # Get all balances
                balances = self.sheets.get_net_balance()
                
                if not balances:
                    return {
                        "success": True,
                        "message": "No active debts found",
                        "data": {"balances": []}
                    }
                
                return {
                    "success": True,
                    "message": "Retrieved all balances",
                    "data": {"balances": balances}
                }
                
        except Exception as e:
            if DEBUG:
                print(f"Error getting balance: {str(e)}")
            return {
                "success": False,
                "message": f"Error getting balance: {str(e)}",
                "data": {}
            }
    
    def settle_debt(self, user_input):
        """
        Process a debt settlement and log an expense if you're paying someone.
        
        Args:
            user_input (str): Natural language input from the user or a settlement data dictionary
            
        Returns:
            dict: Result containing success status and message
        """
        try:
            # Check if user_input is already a dictionary (processed data)
            if isinstance(user_input, dict):
                settlement_data = user_input
            else:
                # Parse the settlement using AI
                settlement_data = self.ai.parse_debt_settlement(user_input)
            
            # Check for parsing errors
            if 'error' in settlement_data:
                return {
                    "success": False,
                    "message": f"Error parsing settlement: {settlement_data['error']}",
                    "data": settlement_data
                }
            
            # Get the person's active debts
            person = settlement_data.get("person")
            if DEBUG:
                print(f"Attempting to settle debt for person: {person}")
                
            active_debts = self.sheets.get_debts_by_person(person, status="active")
            
            if DEBUG:
                print(f"Found {len(active_debts)} active debts for {person}")
                
            if not active_debts:
                return {
                    "success": False,
                    "message": f"No active debts found for {person}",
                    "data": settlement_data
                }
            
            # Get the amount to settle
            amount = settlement_data.get("amount")
            
            # Don't filter by direction - just take the oldest active debt regardless of direction
            # Sort by date (oldest first)
            active_debts.sort(key=lambda x: x.get("Date", ""))
            debt_to_settle = active_debts[0]
            
            if DEBUG:
                print(f"Selected debt to settle: {debt_to_settle}")
            
            # Check if this is a debt where you owe money (direction is "to")
            # If so, log an expense for this payment
            is_you_paying = debt_to_settle.get("Direction", "") == "to"
            
            # Settle the debt
            result = self.sheets.settle_debt(
                debt_to_settle.get("ID"),
                amount=amount,
                settled_date=settlement_data.get("date")
            )
            
            # If you're paying someone, log it as an expense
            if result["success"] and is_you_paying:
                from services.expense import ExpenseService
                expense_service = ExpenseService()
                
                # Create expense data
                expense_data = {
                    "date": settlement_data.get("date", datetime.datetime.now().strftime("%Y-%m-%d")),
                    "description": f"Debt payment to {person}" + (f" for {debt_to_settle.get('Description', '')}" if debt_to_settle.get('Description') else ""),
                    "amount": amount if amount is not None else float(debt_to_settle.get("Amount", 0)),
                    "category": "Debt Payment",
                    "source": "debt_settlement"
                }
                
                # Log the expense
                expense_result = expense_service.sheets.log_expense(expense_data)
                
                # Add expense info to the result data
                if "data" in result:
                    result["data"]["expense_logged"] = expense_result
                    result["data"]["expense_data"] = expense_data
            
            # Add person name to the result data for better messaging
            if result["success"] and "data" in result:
                result["data"]["person"] = person
                result["data"]["is_you_paying"] = is_you_paying
                
                # Get the current balance to show in the message
                try:
                    balance = self.sheets.get_net_balance(person)
                    if balance:
                        result["data"]["new_balance"] = balance["balance"]
                except Exception as e:
                    if DEBUG:
                        print(f"Error getting updated balance: {str(e)}")
            
            return result
                
        except Exception as e:
            if DEBUG:
                print(f"Error settling debt: {str(e)}")
            return {
                "success": False,
                "message": f"Error settling debt: {str(e)}",
                "data": {}
            }
    
    def list_all_balances(self):
        """
        Generate a formatted summary of all outstanding balances.
        
        Returns:
            dict: Result containing success status and message
        """
        try:
            # Get all balances
            balances = self.sheets.get_net_balance()
            
            if not balances:
                return {
                    "success": True,
                    "message": "You have no active debts! 🎉",
                    "data": {"balances": []}
                }
            
            # Format message
            message = "📊 *Current Balances*\n\n"
            
            # Group by direction
            they_owe_you = []
            you_owe_them = []
            
            for balance in balances:
                if balance["they_owe"]:
                    they_owe_you.append(balance)
                elif balance["you_owe"]:
                    you_owe_them.append(balance)
            
            # Sort by amount (highest first)
            they_owe_you.sort(key=lambda x: x["amount"], reverse=True)
            you_owe_them.sort(key=lambda x: x["amount"], reverse=True)
            
            # Add people who owe you
            if they_owe_you:
                message += "*People who owe you:*\n"
                for balance in they_owe_you:
                    message += f"• {balance['person']}: {balance['amount']}\n"
                message += "\n"
            
            # Add people you owe
            if you_owe_them:
                message += "*People you owe:*\n"
                for balance in you_owe_them:
                    message += f"• {balance['person']}: {balance['amount']}\n"
            
            # Calculate net position
            total_owed_to_you = sum(balance["amount"] for balance in they_owe_you)
            total_you_owe = sum(balance["amount"] for balance in you_owe_them)
            net_position = total_owed_to_you - total_you_owe
            
            # Add summary
            message += f"\n*Summary:*\n"
            message += f"Total owed to you: {total_owed_to_you}\n"
            message += f"Total you owe: {total_you_owe}\n"
            message += f"Net position: {net_position} {'(positive)' if net_position >= 0 else '(negative)'}"
            
            return {
                "success": True,
                "message": message,
                "data": {
                    "balances": balances,
                    "total_owed_to_you": total_owed_to_you,
                    "total_you_owe": total_you_owe,
                    "net_position": net_position
                }
            }
                
        except Exception as e:
            if DEBUG:
                print(f"Error listing balances: {str(e)}")
            return {
                "success": False,
                "message": f"Error listing balances: {str(e)}",
                "data": {}
            }