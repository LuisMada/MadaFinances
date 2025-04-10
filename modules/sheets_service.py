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
        
        # Get the client
        client = get_sheets_client()
        
        # Open the spreadsheet by ID
        
        print(f"Opening spreadsheet with ID: {SHEET_ID}")
        spreadsheet = client.open_by_key(SHEET_ID)
        
        # Select the "Expenses" worksheet
        print("Accessing 'Expenses' worksheet...")
        worksheet = spreadsheet.worksheet("Expenses")
        
        # Prepare the row to append
        row = [
            expense_data["Date"],
            expense_data["Description"],
            expense_data["Amount"],
            expense_data["Category"],
            expense_data["Source"]
        ]
        
        print(f"Appending row: {row}")
        # Append the row
        worksheet.append_row(row)
        
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
        
        # Select the "Expenses" worksheet
        worksheet = spreadsheet.worksheet("Expenses")
        
        # Prepare the row to append
        row = [
            expense_data["Date"],
            expense_data["Description"],
            expense_data["Amount"],
            expense_data["Category"],
            expense_data["Source"]
        ]
        
        # Append the row
        worksheet.append_row(row)
        
        return True
        
    except Exception as e:
        raise Exception(f"Error logging expense to Google Sheets: {str(e)}")