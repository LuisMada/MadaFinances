import gspread
from google.oauth2.service_account import Credentials
import os
import traceback
from config import SHEET_ID

def get_sheets_client():
    """
    Authenticate and return a Google Sheets client.
    
    Returns:
        gspread.Client: Authenticated Google Sheets client
    """
    try:
        # Define the scopes
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        # Load credentials from service account file
        credentials_file = 'credentials.json'
        
        if not os.path.exists(credentials_file):
            raise FileNotFoundError(f"Credentials file '{credentials_file}' not found. Please ensure you have placed your Google service account credentials in this file.")
        
        creds = Credentials.from_service_account_file(
            credentials_file, 
            scopes=scopes
        )
        
        # Create and return the gspread client
        return gspread.authorize(creds)
    
    except Exception as e:
        print(f"Error creating Google Sheets client: {str(e)}")
        traceback.print_exc()
        raise Exception(f"Failed to authenticate with Google Sheets: {str(e)}")

def get_worksheet(sheet_name):
    """
    Get a specific worksheet by name.
    
    Args:
        sheet_name (str): Name of the worksheet to retrieve
        
    Returns:
        gspread.Worksheet: The requested worksheet
    """
    client = get_sheets_client()
    spreadsheet = client.open_by_key(SHEET_ID)
    return spreadsheet.worksheet(sheet_name)

def get_all_rows(sheet_name):
    """
    Get all rows from a specific worksheet.
    
    Args:
        sheet_name (str): Name of the worksheet to retrieve data from
        
    Returns:
        list: List of all rows in the worksheet
    """
    worksheet = get_worksheet(sheet_name)
    return worksheet.get_all_values()

def append_row(sheet_name, row_data):
    """
    Append a row to a specific worksheet.
    
    Args:
        sheet_name (str): Name of the worksheet to append to
        row_data (list): List of values to append as a row
        
    Returns:
        bool: True if successful
    """
    worksheet = get_worksheet(sheet_name)
    worksheet.append_row(row_data)
    return True

def log_expense(expense_data):
    """
    Log an expense to Google Sheets.
    
    Args:
        expense_data (dict): Dictionary containing expense details
            Required keys: Date, Description, Amount, Category, Source
    
    Returns:
        bool: True if successful
    """
    try:
        # Print debug info
        print("Attempting to log expense to Google Sheets...")
        print(f"Expense data: {expense_data}")
        
        # Prepare the row to append
        row = [
            expense_data["Date"],
            expense_data["Description"],
            expense_data["Amount"],
            expense_data["Category"],
            expense_data["Source"]
        ]
        
        # Use the new append_row helper function
        print(f"Appending row: {row}")
        append_row("Expenses", row)
        
        print("Successfully logged expense to Google Sheets")
        return True
        
    except FileNotFoundError as e:
        print(f"File not found error: {str(e)}")
        traceback.print_exc()
        raise Exception(f"Error logging expense to Google Sheets: {str(e)}")
    except Exception as e:
        print(f"Error logging expense to Google Sheets: {str(e)}")
        traceback.print_exc()
        raise Exception(f"Error logging expense to Google Sheets: {str(e)}")