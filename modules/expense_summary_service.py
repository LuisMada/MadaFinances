"""
Expense summary service for the financial tracker.
This module handles parsing time periods and generating expense summaries.
"""
import datetime
from dateutil.relativedelta import relativedelta
from openai import OpenAI
import json
import pandas as pd
from modules import sheets_service
from config import OPENAI_API_KEY
from config import SHEET_ID

def parse_time_period(query):
    """
    Parse a natural language time period using OpenAI.
    
    Args:
        query (str): Natural language time period (e.g., "this week", "last month")
        
    Returns:
        dict: Dictionary with start_date and end_date as datetime objects
    """
    try:
        # Create a client instance
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        # Current date for reference
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        
        # Extract time period - ENHANCED PROMPT
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system", 
                    "content": "You are a financial assistant that extracts date ranges from queries with precision."
                },
                {
                    "role": "user", 
                    "content": f"""Given this query about expenses: '{query}'
                    
                    Extract the time period mentioned and convert it to a specific date range.
                    Today's date is {today}.
                    
                    Return ONLY a JSON with these fields:
                    - start_date: the start date in YYYY-MM-DD format
                    - end_date: the end date in YYYY-MM-DD format
                    - period_name: a human-readable name for this period (e.g., "This Week", "March 2025")
                    
                    Handle these time period formats:
                    - Standard periods: "this week", "this month", "last month", "today", "yesterday"
                    - Specific months: "January", "February", "March 2025"
                    - Relative periods: "last 7 days", "past 30 days", "previous quarter"
                    - Seasons: "this summer", "last winter"
                    - Years: "2024", "this year", "last year"
                    - Quarters: "Q1", "first quarter", "last quarter"
                    - Date ranges: "from January to March", "between April 1 and April 10"
                    - Single days: "on Monday", "April 5th"
                    
                    Examples:
                    - For "Show me expenses this week", return dates from the start of the current week to today
                    - For "Expenses in March", return dates from March 1 to March 31 of the current year
                    - For "Last month's spending", return the entire previous month
                    - For "Expenses from March 1 to April 10", return that exact date range
                    - For "Last quarter expenses", return the previous 3-month quarter
                    - For "Spending during Holy Week", determine the date range for Holy Week in the current year
                    - If no specific time period is mentioned, default to the current month
                    
                    Be precise with the dates based on the query.
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
        period_data = json.loads(content)
        
        # Convert string dates to datetime objects
        start_date = datetime.datetime.strptime(period_data["start_date"], "%Y-%m-%d").date()
        end_date = datetime.datetime.strptime(period_data["end_date"], "%Y-%m-%d").date()
        period_name = period_data["period_name"]
        
        return {
            "start_date": start_date,
            "end_date": end_date,
            "period_name": period_name
        }
        
    except Exception as e:
        print(f"Error parsing time period: {str(e)}")
        
        # Default to current month if parsing fails
        today = datetime.date.today()
        start_date = today.replace(day=1)
        
        # Handle end of month calculation
        if today.month == 12:
            next_month = datetime.date(today.year + 1, 1, 1)
        else:
            next_month = datetime.date(today.year, today.month + 1, 1)
            
        end_date = next_month - datetime.timedelta(days=1)
        
        return {
            "start_date": start_date,
            "end_date": today,  # Use today as end date instead of month end
            "period_name": f"This Month ({today.strftime('%B %Y')})"
        }

def get_expenses_in_period(start_date, end_date):
    """
    Get expenses within a specified date range from Google Sheets.
    
    Args:
        start_date (datetime.date): Start date for the query
        end_date (datetime.date): End date for the query
        
    Returns:
        pandas.DataFrame: DataFrame containing expenses in the period
    """
    try:
        # Get the client
        client = sheets_service.get_sheets_client()
        
        # Open the spreadsheet
        
        spreadsheet = client.open_by_key(SHEET_ID)
        
        # Get the expenses sheet
        expenses_sheet = spreadsheet.worksheet("Expenses")
        
        # Get all data
        data = expenses_sheet.get_all_values()
        
        # Check if there's any data
        if not data or len(data) <= 1:  # Only header row or empty
            return pd.DataFrame(columns=["Date", "Description", "Amount", "Category", "Source"])
        
        # Convert to DataFrame
        df = pd.DataFrame(data[1:], columns=data[0])
        
        # Ensure the 'Date' column uses datetime format
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        
        # Filter rows between start_date and end_date (inclusive)
        start_datetime = pd.Timestamp(start_date)
        end_datetime = pd.Timestamp(end_date)
        
        filtered_df = df[(df['Date'] >= start_datetime) & (df['Date'] <= end_datetime)]
        
        # Convert Amount to numeric
        filtered_df['Amount'] = pd.to_numeric(filtered_df['Amount'], errors='coerce')
        
        return filtered_df
        
    except Exception as e:
        print(f"Error getting expenses from Google Sheets: {str(e)}")
        raise Exception(f"Failed to retrieve expenses: {str(e)}")

# The rest of the file remains unchanged
def generate_summary(df):
    """
    Generate summary statistics from expense data.
    
    Args:
        df (pandas.DataFrame): DataFrame containing expense data
        
    Returns:
        dict: Dictionary containing summary statistics
    """
    # Check if DataFrame is empty
    if df.empty:
        return {
            "total_expenses": 0,
            "average_expense": 0,
            "num_transactions": 0,
            "by_category": {},
            "data_available": False
        }
    
    # Calculate total expenses
    total_expenses = df['Amount'].sum()
    
    # Calculate average expense
    average_expense = df['Amount'].mean()
    
    # Count number of transactions
    num_transactions = len(df)
    
    # Group by category
    by_category = df.groupby('Category')['Amount'].sum().to_dict()
    
    # Sort categories by amount (descending)
    sorted_categories = sorted(by_category.items(), key=lambda x: x[1], reverse=True)
    
    # Convert to ordered dictionary
    by_category = {k: v for k, v in sorted_categories}
    
    # Add percentage of total for each category
    for category in by_category:
        by_category[category] = {
            "amount": round(by_category[category], 2),
            "percentage": round((by_category[category] / total_expenses) * 100, 1)
        }
    
    # Create summary
    summary = {
        "total_expenses": round(total_expenses, 2),
        "average_expense": round(average_expense, 2),
        "num_transactions": num_transactions,
        "by_category": by_category,
        "data_available": True
    }
    
    return summary

def format_summary_response(summary, period):
    """
    Format the expense summary into a well-structured, readable response.
    Uses Philippine Peso (₱) as the currency.
    
    Args:
        summary (dict): Dictionary containing summary statistics
        period (dict): Dictionary containing time period information
        
    Returns:
        str: Formatted response string
    """
    if not summary["data_available"]:
        return f"📊 **Expense Summary for {period['period_name']}**\n\nNo expenses found for this period."
    
    # Create a well-formatted, clearly spaced summary with Peso symbol
    response = f"📊 **Expense Summary for {period['period_name']}**\n\n"
    
    # Key metrics section with clear labeling using ₱ symbol
    response += f"**Total Expenses:** ₱{summary['total_expenses']:.2f}\n"
    response += f"**Number of Transactions:** {summary['num_transactions']}\n"
    response += f"**Average Expense:** ₱{summary['average_expense']:.2f}\n\n"
    
    # Category breakdown with consistent formatting
    response += "**Breakdown by Category:**\n"
    for category, data in summary["by_category"].items():
        # Format with consistent spacing and clear percentage, using Peso symbol
        response += f"• **{category}:** ₱{data['amount']:.2f} ({data['percentage']:.1f}%)\n"
    
    return response

def handle_expense_summary(query):
    """
    Handle a request for an expense summary.
    
    Args:
        query (str): Natural language query about expenses
        
    Returns:
        tuple: (summary dict, formatted response string, time period dict)
    """
    try:
        # Parse the time period from the query
        period = parse_time_period(query)
        
        # Get expenses for the period
        df = get_expenses_in_period(period["start_date"], period["end_date"])
        
        # Generate summary statistics
        summary = generate_summary(df)
        
        # Format the response using the dedicated formatter
        response = format_summary_response(summary, period)
        
        return summary, response, period
        
    except Exception as e:
        error_msg = f"Error generating expense summary: {str(e)}"
        print(error_msg)
        return None, error_msg, None