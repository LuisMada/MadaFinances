"""
Budget management service for the financial tracker.
This module handles creating, retrieving, and analyzing budget data.
"""
import datetime
from dateutil.relativedelta import relativedelta
import pandas as pd
from modules import sheets_service

# Sheet name for budgets
BUDGETS_SHEET = "Budgets"
from config import SHEET_ID

def ensure_budgets_sheet():
    """
    Ensure that the Budgets sheet exists in the spreadsheet.
    Creates it if it doesn't exist.
    """
    try:
        # Get the client
        client = sheets_service.get_sheets_client()
        
        # Open the spreadsheet by ID

        spreadsheet = client.open_by_key(SHEET_ID)
        
        # Check if Budgets sheet exists
        sheet_exists = False
        for sheet in spreadsheet.worksheets():
            if sheet.title == BUDGETS_SHEET:
                sheet_exists = True
                break
                
        if sheet_exists:
            print(f"{BUDGETS_SHEET} sheet exists")
        else:
            # Create the sheet
            print(f"Creating {BUDGETS_SHEET} sheet")
            budget_sheet = spreadsheet.add_worksheet(
                title=BUDGETS_SHEET, 
                rows=20, 
                cols=5
            )
            
            # Add headers
            budget_sheet.update('A1:E1', [['Amount', 'Period', 'Category', 'StartDate', 'Active']])
            
            # Add default total budget
            today = datetime.date.today()
            default_budget = [
                ["1000", "Monthly", "Total", today.strftime("%Y-%m-%d"), "True"]
            ]
            budget_sheet.update('A2:E2', default_budget)
            
        return True
        
    except Exception as e:
        print(f"Error ensuring budgets sheet: {str(e)}")
        return False

def get_budgets():
    """
    Get all active budgets from the Budgets sheet.
    
    Returns:
        pandas.DataFrame: DataFrame containing budget data
    """
    try:
        # Ensure the sheet exists
        ensure_budgets_sheet()
        
        # Get the client
        client = sheets_service.get_sheets_client()
        

        spreadsheet = client.open_by_key(SHEET_ID)
        
        # Get the budgets sheet
        budgets_sheet = spreadsheet.worksheet(BUDGETS_SHEET)
        
        # Get all values
        data = budgets_sheet.get_all_values()
        
        # Check if there's any data
        if not data or len(data) <= 1:  # Only header row or empty
            return pd.DataFrame(columns=["Amount", "Period", "Category", "StartDate", "Active"])
        
        # Convert to DataFrame
        df = pd.DataFrame(data[1:], columns=data[0])
        
        # Filter active budgets
        df = df[df['Active'].str.lower() == 'true']
        
        # Convert Amount to numeric
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce')
        
        # Convert StartDate to datetime
        df['StartDate'] = pd.to_datetime(df['StartDate'], errors='coerce')
        
        return df
        
    except Exception as e:
        print(f"Error getting budgets: {str(e)}")
        # Return empty DataFrame on error
        return pd.DataFrame(columns=["Amount", "Period", "Category", "StartDate", "Active"])

def set_budget(amount, period, category="Total"):
    """
    Set a budget amount for a category and period.
    If a budget already exists for the category and period, it updates it.
    Otherwise, it creates a new budget entry.
    
    Args:
        amount (float): Budget amount
        period (str): "Weekly" or "Monthly"
        category (str, optional): Category name or "Total" for overall budget
        
    Returns:
        bool: True if successful
    """
    try:
        # Validate inputs
        if amount <= 0:
            raise ValueError("Budget amount must be positive")
            
        if period.lower() not in ["weekly", "monthly"]:
            raise ValueError("Period must be 'Weekly' or 'Monthly'")
        
        # Standardize period
        period = period.capitalize()
        
        # Ensure the sheet exists
        ensure_budgets_sheet()
        
        # Get the client
        client = sheets_service.get_sheets_client()
        
        # Open the spreadsheet
        SHEET_ID = "10c4U63Od8Im3E2HP5NKReio6wafWbfJ_zsGJRKHB1LY"
        spreadsheet = client.open_by_key(SHEET_ID)
        
        # Get the budgets sheet
        budgets_sheet = spreadsheet.worksheet(BUDGETS_SHEET)
        
        # Get existing budgets
        df = get_budgets()
        
        # Today's date
        today = datetime.date.today().strftime("%Y-%m-%d")
        
        # Check if budget exists for the category and period
        matching_budgets = df[(df['Category'] == category) & (df['Period'] == period)]
        
        if not matching_budgets.empty:
            # Update existing budget
            # Find the row in the sheet
            all_data = budgets_sheet.get_all_values()
            
            for i, row in enumerate(all_data):
                if (i > 0 and  # Skip header
                    row[2] == category and  # Category
                    row[1] == period and  # Period
                    row[4].lower() == 'true'):  # Active
                    
                    # Update amount and start date
                    budgets_sheet.update_cell(i + 1, 1, str(amount))  # Amount column
                    budgets_sheet.update_cell(i + 1, 4, today)  # StartDate column
                    break
        else:
            # Add new budget
            budgets_sheet.append_row([
                str(amount),
                period,
                category,
                today,
                "True"
            ])
        
        return True
        
    except Exception as e:
        print(f"Error setting budget: {str(e)}")
        raise Exception(f"Failed to set budget: {str(e)}")

def get_budget_status(start_date, end_date, week_start_index=0):
    """
    Get budget status for a specified date range.
    For weekly budgets, uses the specified week start day.
    
    Args:
        start_date (datetime.date): Start date for the query
        end_date (datetime.date): End date for the query
        week_start_index (int, optional): Day of week that starts the week (0=Monday, 6=Sunday). Defaults to 0 (Monday).
        
    Returns:
        dict: Dictionary containing budget status information
    """
    from modules import expense_summary_service
    
    try:
        # Get expenses for the period
        expense_df = expense_summary_service.get_expenses_in_period(start_date, end_date)
        
        # Generate expense summary
        expense_summary = expense_summary_service.generate_summary(expense_df)
        
        # Get active budgets
        budget_df = get_budgets()
        
        if budget_df.empty:
            return {
                "has_budget": False,
                "message": "No budgets found. Set a budget first."
            }
        
        # Calculate days in period
        days_in_period = (end_date - start_date).days + 1
        days_elapsed = min((datetime.date.today() - start_date).days + 1, days_in_period)
        days_remaining = max(0, days_in_period - days_elapsed)
        
        # Initialize results
        budget_status = {
            "has_budget": True,
            "total_budget": 0,
            "total_spent": expense_summary["total_expenses"],
            "remaining": 0,
            "days_in_period": days_in_period,
            "days_elapsed": days_elapsed,
            "days_remaining": days_remaining,
            "daily_budget": 0,
            "weekly_budget": 0,
            "daily_average": expense_summary["total_expenses"] / max(1, days_elapsed),
            "remaining_daily_allowance": 0,
            "percent_used": 0,
            "status": "under_budget",  # under_budget, near_limit, over_budget
            "categories": {},
            "week_start_index": week_start_index  # Store the week start index for reference
        }
        
        # Determine if period is closer to a week or a month
        is_weekly_period = days_in_period <= 14  # Use weekly for up to 2 weeks
        is_monthly_period = days_in_period > 14  # Use monthly for longer periods
        
        # Get total budgets by period type
        total_budgets = budget_df[budget_df['Category'] == 'Total']
        
        if not total_budgets.empty:
            weekly_budget_row = None
            monthly_budget_row = None
            
            # Find the most recent budget of each period type
            for _, row in total_budgets.iterrows():
                if row['Period'].lower() == 'weekly' and (weekly_budget_row is None or row['StartDate'] > weekly_budget_row['StartDate']):
                    weekly_budget_row = row
                elif row['Period'].lower() == 'monthly' and (monthly_budget_row is None or row['StartDate'] > monthly_budget_row['StartDate']):
                    monthly_budget_row = row
            
            # If we have a weekly budget, calculate based on current week boundaries with custom start day
            if weekly_budget_row is not None and is_weekly_period:
                # Calculate the current week boundaries based on the configured start day
                today = datetime.date.today()
                weekday = today.weekday()  # 0 = Monday, 6 = Sunday
                
                # Calculate days from today to the most recent week start
                days_since_week_start = (weekday - week_start_index) % 7
                current_week_start = today - datetime.timedelta(days=days_since_week_start)
                
                # Find the upcoming week end (6 days after start)
                days_until_week_end = 6 - days_since_week_start
                current_week_end = today + datetime.timedelta(days=days_until_week_end)
                
                # Get expenses for current week only
                current_week_expenses = expense_summary_service.get_expenses_in_period(
                    current_week_start, 
                    current_week_end
                )
                current_week_summary = expense_summary_service.generate_summary(current_week_expenses)
                
                # Use the weekly budget 
                weekly_budget = weekly_budget_row['Amount']
                
                # Calculate budget metrics
                budget_status["weekly_budget"] = weekly_budget
                budget_status["total_budget"] = weekly_budget
                budget_status["budget_period_type"] = 'weekly'
                budget_status["week_start_date"] = current_week_start
                budget_status["week_end_date"] = current_week_end
                budget_status["total_spent"] = current_week_summary["total_expenses"]
                budget_status["remaining"] = weekly_budget - current_week_summary["total_expenses"]
                
                # Update days for the week
                days_in_week = 7
                days_elapsed_in_week = days_since_week_start + 1  # Including today
                days_remaining_in_week = days_in_week - days_elapsed_in_week
                
                budget_status["days_in_period"] = days_in_week
                budget_status["days_elapsed"] = days_elapsed_in_week
                budget_status["days_remaining"] = days_remaining_in_week
                
                # Calculate daily metrics
                budget_status["daily_budget"] = weekly_budget / days_in_week
                
                if current_week_summary["data_available"]:
                    budget_status["daily_average"] = current_week_summary["total_expenses"] / max(1, days_elapsed_in_week)
                else:
                    budget_status["daily_average"] = 0
                
                if days_remaining_in_week > 0:
                    budget_status["remaining_daily_allowance"] = max(0, budget_status["remaining"]) / days_remaining_in_week
                else:
                    budget_status["remaining_daily_allowance"] = 0
                
                # If we also have a monthly budget, include it for reference
                if monthly_budget_row is not None:
                    budget_status["monthly_budget"] = monthly_budget_row['Amount']
                else:
                    # Calculate monthly equivalent
                    budget_status["monthly_equivalent"] = weekly_budget * 4.33
            
            # If we don't have a weekly budget or if period is closer to a month, use monthly
            elif monthly_budget_row is not None:
                # Use monthly budget (prorated if needed)
                monthly_budget = monthly_budget_row['Amount']
                
                # For monthly view, use the actual selected period
                if is_monthly_period:
                    # Prorate for partial months
                    if days_in_period < 28:
                        budget_amount = monthly_budget * (days_in_period / 30)
                    else:
                        budget_amount = monthly_budget
                        
                    budget_status["budget_period_type"] = 'monthly'
                else:
                    # For shorter periods, prorate the monthly budget
                    budget_amount = monthly_budget * (days_in_period / 30)
                    budget_status["budget_period_type"] = 'monthly (prorated)'
                
                budget_status["monthly_budget"] = monthly_budget
                budget_status["total_budget"] = budget_amount
                budget_status["remaining"] = budget_amount - budget_status["total_spent"]
                budget_status["daily_budget"] = budget_amount / days_in_period
                
                # Calculate weekly equivalent for reference
                budget_status["weekly_budget"] = monthly_budget / 4.33
                
            # If only weekly budget exists but period is not weekly
            elif weekly_budget_row is not None:
                weekly_budget = weekly_budget_row['Amount']
                
                if is_monthly_period:
                    # Convert weekly to monthly equivalent
                    budget_amount = weekly_budget * 4.33
                    budget_status["budget_period_type"] = 'monthly (from weekly)'
                else:
                    # Prorate for the period
                    budget_amount = weekly_budget * (days_in_period / 7)
                    budget_status["budget_period_type"] = 'weekly (prorated)'
                
                budget_status["weekly_budget"] = weekly_budget
                budget_status["total_budget"] = budget_amount
                budget_status["remaining"] = budget_amount - budget_status["total_spent"]
                budget_status["daily_budget"] = budget_amount / days_in_period
                
                # Calculate monthly equivalent for reference
                budget_status["monthly_equivalent"] = weekly_budget * 4.33
            
            else:
                # Should never reach here as we already checked if total_budgets is empty
                budget_amount = 0
                budget_status["budget_period_type"] = 'unknown'
            
            # Calculate remaining daily allowance if needed
            if "remaining_daily_allowance" not in budget_status and days_remaining > 0:
                budget_status["remaining_daily_allowance"] = max(0, budget_status["remaining"]) / days_remaining
            
            # Calculate percent used
            if budget_status["total_budget"] > 0:
                budget_status["percent_used"] = (budget_status["total_spent"] / budget_status["total_budget"]) * 100
                
                # Determine status
                if budget_status["percent_used"] > 100:
                    budget_status["status"] = "over_budget"
                elif budget_status["percent_used"] > 85:
                    budget_status["status"] = "near_limit"
                else:
                    budget_status["status"] = "under_budget"
        
        # Process category budgets - this section would continue with the existing logic
        # ...
        
        return budget_status
        
    except Exception as e:
        print(f"Error getting budget status: {str(e)}")
        return {
            "has_budget": False,
            "error": str(e)
        }

def format_budget_status_response(budget_status):
    """
    Format the budget status into a well-structured, readable response.
    Uses Philippine Peso (₱) as the currency. Includes week start day information when relevant.
    
    Args:
        budget_status (dict): Dictionary containing budget information
        
    Returns:
        str: Formatted response string
    """
    if not budget_status.get("has_budget", False):
        return "📊 **Budget Status**\n\nNo budgets found. Set a budget first with a command like 'Set ₱1000 monthly budget'."
    
    # Create a well-formatted summary
    response = "📊 **Budget Status**\n\n"
    
    # Overall budget status
    days_elapsed = budget_status.get("days_elapsed", 0)
    days_remaining = budget_status.get("days_remaining", 0)
    
    # Format the status emoji
    status_emoji = "✅"  # under_budget
    if budget_status.get("status") == "over_budget":
        status_emoji = "❌"
    elif budget_status.get("status") == "near_limit":
        status_emoji = "⚠️"
    
    # Add period type if available
    period_type = budget_status.get("budget_period_type", "")
    period_label = f"{period_type.capitalize()} " if period_type else ""
    
    # Get week start day information for weekly budgets
    week_info = ""
    if period_type.lower().startswith('weekly') and "week_start_index" in budget_status:
        week_start_index = budget_status.get("week_start_index", 0)
        weekday_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        week_start_day = weekday_names[week_start_index] if 0 <= week_start_index <= 6 else "Monday"
        week_info = f" (Weeks start on {week_start_day})"
    
    response += f"{status_emoji} **Overall {period_label}Budget{week_info}:** ₱{budget_status['total_budget']:.2f}\n"
    response += f"💰 **Spent so far:** ₱{budget_status['total_spent']:.2f} ({budget_status['percent_used']:.1f}%)\n"
    response += f"🔢 **Remaining:** ₱{budget_status['remaining']:.2f}\n"
    response += f"⏳ **Period Progress:** {days_elapsed} of {budget_status.get('days_in_period', 0)} days ({(days_elapsed/max(1, budget_status.get('days_in_period', 1)))*100:.1f}%)\n\n"
    
    # Add weekly budget info if not a weekly view
    if period_type.lower() != "weekly" and "weekly_budget" in budget_status:
        response += f"📅 **Weekly Budget:** ₱{budget_status['weekly_budget']:.2f}\n\n"
    
    # Daily averages
    response += "📅 **Daily Breakdown:**\n"
    response += f"• Budget per day: ₱{budget_status['daily_budget']:.2f}\n"
    response += f"• Average spent per day: ₱{budget_status['daily_average']:.2f}\n"
    
    if days_remaining > 0:
        response += f"• Remaining daily allowance: ₱{budget_status['remaining_daily_allowance']:.2f}\n\n"
    else:
        response += "\n"
    
    # Category breakdown
    if budget_status.get("categories"):
        response += "📊 **Category Budgets:**\n"
        
        for category, data in budget_status["categories"].items():
            cat_emoji = "✅"  # under_budget
            if data["status"] == "over_budget":
                cat_emoji = "❌"
            elif data["status"] == "near_limit":
                cat_emoji = "⚠️"
                
            response += f"{cat_emoji} **{category}:** ₱{data['spent']:.2f} of ₱{data['budget']:.2f} ({data['percent_used']:.1f}%)\n"
    
    return response