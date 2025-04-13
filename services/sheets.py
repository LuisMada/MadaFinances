"""
Google Sheets Service
Provides CRUD operations for the Google Sheets backend.
"""

import gspread
from google.oauth2.service_account import Credentials
import os
import datetime
import traceback
from config import (
    SHEET_ID, 
    CREDENTIALS_FILE, 
    DEFAULT_CATEGORIES,
    EXPENSES_SHEET,
    CATEGORIES_SHEET,
    BUDGETS_SHEET,
    PREFERENCES_SHEET,
    DEBUG
)

import ssl

# Create an unverified context
ssl._create_default_https_context = ssl._create_unverified_context

class SheetsService:
    def __init__(self):
        """Initialize the Google Sheets service."""
        self.client = self._get_client()
        self.spreadsheet = self.client.open_by_key(SHEET_ID)
        self._ensure_sheets_exist()
        
    
    def _get_client(self):
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
            if not os.path.exists(CREDENTIALS_FILE):
                raise FileNotFoundError(
                    f"Credentials file '{CREDENTIALS_FILE}' not found. Please ensure you have placed "
                    "your Google service account credentials in this file."
                )
            
            creds = Credentials.from_service_account_file(
                CREDENTIALS_FILE, 
                scopes=scopes
            )
            
            # Create and return the gspread client
            return gspread.authorize(creds)
        
        except Exception as e:
            print(f"Error creating Google Sheets client: {str(e)}")
            traceback.print_exc()
            raise Exception(f"Failed to authenticate with Google Sheets: {str(e)}")
    
    def _ensure_sheets_exist(self):
        """Create necessary worksheets if they don't exist."""
        try:
            # Get all worksheet titles
            worksheet_titles = [ws.title for ws in self.spreadsheet.worksheets()]
            
            # Check and create Expenses sheet
            if EXPENSES_SHEET not in worksheet_titles:
                self.spreadsheet.add_worksheet(title=EXPENSES_SHEET, rows=1000, cols=20)
                expenses_sheet = self.spreadsheet.worksheet(EXPENSES_SHEET)
                expenses_sheet.append_row(["Date", "Description", "Amount", "Category", "Source"])
                print(f"Created {EXPENSES_SHEET} worksheet")
                
            # Check and create Categories sheet
            if CATEGORIES_SHEET not in worksheet_titles:
                self.spreadsheet.add_worksheet(title=CATEGORIES_SHEET, rows=100, cols=2)
                categories_sheet = self.spreadsheet.worksheet(CATEGORIES_SHEET)
                categories_sheet.append_row(["Category", "Description"])
                
                # Add default categories
                for category in DEFAULT_CATEGORIES:
                    categories_sheet.append_row([category, ""])
                
                print(f"Created {CATEGORIES_SHEET} worksheet with default categories")
                
            # Check and create Budgets sheet
            if BUDGETS_SHEET not in worksheet_titles:
                self.spreadsheet.add_worksheet(title=BUDGETS_SHEET, rows=100, cols=20)
                budgets_sheet = self.spreadsheet.worksheet(BUDGETS_SHEET)
                budgets_sheet.append_row(["Amount", "Period", "Category", "StartDate", "Active"])
                print(f"Created {BUDGETS_SHEET} worksheet")
                
            # Check and create Preferences sheet
            if PREFERENCES_SHEET not in worksheet_titles:
                self.spreadsheet.add_worksheet(title=PREFERENCES_SHEET, rows=100, cols=3)
                preferences_sheet = self.spreadsheet.worksheet(PREFERENCES_SHEET)
                preferences_sheet.append_row(["UserID", "Setting", "Value"])
                print(f"Created {PREFERENCES_SHEET} worksheet")
                
        except Exception as e:
            print(f"Error ensuring sheets exist: {str(e)}")
            traceback.print_exc()
    
    # Expense Methods
    def log_expense(self, expense_data):
        """
        Log an expense to Google Sheets.
        
        Args:
            expense_data (dict): Dictionary containing expense details
                Required keys: date, description, amount, category, source
        
        Returns:
            bool: True if successful
        """
        try:
            if DEBUG:
                print(f"Logging expense to Google Sheets: {expense_data}")
            
            # Select the "Expenses" worksheet
            worksheet = self.spreadsheet.worksheet(EXPENSES_SHEET)
            
            # Prepare the row to append
            row = [
                expense_data["date"],
                expense_data["description"],
                expense_data["amount"],
                expense_data["category"],
                expense_data["source"]
            ]
            
            # Append the row
            worksheet.append_row(row)
            
            if DEBUG:
                print("Successfully logged expense to Google Sheets")
            
            return True
            
        except Exception as e:
            print(f"Error logging expense to Google Sheets: {str(e)}")
            traceback.print_exc()
            raise Exception(f"Error logging expense to Google Sheets: {str(e)}")
    
    def get_expenses_in_date_range(self, start_date, end_date, category=None):
        """
        Retrieve expenses between specific dates, optionally filtered by category.
        
        Args:
            start_date (datetime.date): Start date for filtering (inclusive)
            end_date (datetime.date): End date for filtering (inclusive)
            category (str, optional): Category to filter by
        
        Returns:
            list: List of expense dictionaries
        """
        try:
            # Select the "Expenses" worksheet
            worksheet = self.spreadsheet.worksheet(EXPENSES_SHEET)
            
            # Get all values including headers
            all_values = worksheet.get_all_values()
            
            # Check if there's data (should be at least headers)
            if len(all_values) <= 1:
                return []
                
            # Extract headers and data
            headers = all_values[0]
            data = all_values[1:]
            
            # Convert to list of dictionaries
            expenses = []
            for row in data:
                expense = dict(zip(headers, row))
                expenses.append(expense)
            
            # Filter by date range
            filtered_expenses = []
            for expense in expenses:
                expense_date = self._date_from_str(expense.get('Date'))
                if start_date <= expense_date <= end_date:
                    filtered_expenses.append(expense)
            
            # Apply category filter if provided
            if category and category.lower() != 'all':
                filtered_expenses = [exp for exp in filtered_expenses if exp.get('Category') == category]
                    
            return filtered_expenses
            
        except Exception as e:
            print(f"Error retrieving expenses in date range: {str(e)}")
            traceback.print_exc()
            return []
    
    def delete_expense(self, expense_identifier):
        """
        Delete an expense by matching the identifier with description.
        
        Args:
            expense_identifier (str): Text to match against expense descriptions
            
        Returns:
            bool: True if at least one expense was deleted
        """
        try:
            # Select the "Expenses" worksheet
            worksheet = self.spreadsheet.worksheet(EXPENSES_SHEET)
            
            # Get all values including headers
            all_values = worksheet.get_all_values()
            
            # Check if there's data (should be at least headers)
            if len(all_values) <= 1:
                return False
                
            # Extract headers and data
            headers = all_values[0]
            data = all_values[1:]
            
            # Find the index of the Description column
            desc_index = headers.index("Description") if "Description" in headers else 1
            
            # Find rows to delete
            rows_to_delete = []
            for i, row in enumerate(data):
                if expense_identifier.lower() in row[desc_index].lower():
                    # Add 2 to account for 1-based indexing and header row
                    rows_to_delete.append(i + 2)
            
            # Delete rows in reverse order to avoid shifting issues
            rows_to_delete.sort(reverse=True)
            for row_index in rows_to_delete:
                worksheet.delete_rows(row_index)
            
            return len(rows_to_delete) > 0
            
        except Exception as e:
            print(f"Error deleting expense: {str(e)}")
            traceback.print_exc()
            return False
    
    # Category Methods
    def get_categories(self):
        """
        Retrieve all expense categories.
        
        Returns:
            list: List of category names
        """
        try:
            # Select the "Categories" worksheet
            worksheet = self.spreadsheet.worksheet(CATEGORIES_SHEET)
            
            # Get all values including headers
            all_values = worksheet.get_all_values()
            
            # Check if there's data (should be at least headers)
            if len(all_values) <= 1:
                return DEFAULT_CATEGORIES
                
            # Extract category names (first column, skipping header)
            categories = [row[0] for row in all_values[1:] if row[0]]
            
            return categories if categories else DEFAULT_CATEGORIES
            
        except Exception as e:
            print(f"Error retrieving categories: {str(e)}")
            traceback.print_exc()
            return DEFAULT_CATEGORIES
    
    # Budget Methods
    def set_budget(self, budget_data):
        """
        Create or update a budget, including custom periods.
        
        Args:
            budget_data (dict): Dictionary containing budget details
                Required keys: amount, period, category, start_date
                Optional keys: days (for custom periods), active
        
        Returns:
            bool: True if successful
        """
        try:
            if DEBUG:
                print(f"Setting budget in Google Sheets: {budget_data}")
            
            # Select the "Budgets" worksheet
            worksheet = self.spreadsheet.worksheet(BUDGETS_SHEET)
            
            # Get all values including headers
            all_values = worksheet.get_all_values()
            
            # Extract headers
            if not all_values:
                # Create headers if sheet is empty
                headers = ["Amount", "Period", "Category", "StartDate", "Active", "Days"]
                worksheet.append_row(headers)
                print(f"Created headers in {BUDGETS_SHEET} worksheet")
                all_values = [headers]
            else:
                headers = all_values[0]
            
            if DEBUG:
                print(f"Found headers: {headers}")
            
            # Ensure all required fields are present
            required_fields = ["amount", "period", "category", "start_date"]
            for field in required_fields:
                if field not in budget_data:
                    print(f"Missing required field: {field}")
                    return False
            
            # Find indexes for key columns (case insensitive)
            amount_index = None
            category_index = None
            period_index = None
            active_index = None
            startdate_index = None
            days_index = None
            
            for i, header in enumerate(headers):
                header_lower = header.lower()
                if header_lower == "amount":
                    amount_index = i
                elif header_lower == "category":
                    category_index = i
                elif header_lower == "period":
                    period_index = i
                elif header_lower == "active":
                    active_index = i
                elif header_lower == "startdate":
                    startdate_index = i
                elif header_lower == "days":
                    days_index = i
            
            # If indexes weren't found, add columns and set indexes
            if amount_index is None:
                headers.append("Amount")
                worksheet.update_cell(1, len(headers), "Amount")
                amount_index = len(headers) - 1
                print(f"Added 'Amount' column at index {amount_index + 1}")
                
            if category_index is None:
                headers.append("Category")
                worksheet.update_cell(1, len(headers), "Category")
                category_index = len(headers) - 1
                
            if period_index is None:
                headers.append("Period")
                worksheet.update_cell(1, len(headers), "Period")
                period_index = len(headers) - 1
                
            if active_index is None:
                headers.append("Active")
                worksheet.update_cell(1, len(headers), "Active")
                active_index = len(headers) - 1
                
            if startdate_index is None:
                headers.append("StartDate")
                worksheet.update_cell(1, len(headers), "StartDate")
                startdate_index = len(headers) - 1
                
            if days_index is None:
                headers.append("Days")
                worksheet.update_cell(1, len(headers), "Days")
                days_index = len(headers) - 1
            
            # Log the column indexes for debugging
            if DEBUG:
                print(f"Column indexes: Amount={amount_index}, Category={category_index}, "
                    f"Period={period_index}, Active={active_index}, "
                    f"StartDate={startdate_index}, Days={days_index}")
            
            # Check for existing budget entries for this category and period
            existing_row = None
            for i, row in enumerate(all_values[1:], start=2):  # Start from 2 to account for header
                if len(row) <= max(category_index, period_index, active_index):
                    continue  # Skip rows that don't have enough columns
                
                row_category = row[category_index].lower() if category_index < len(row) else ""
                row_period = row[period_index].lower() if period_index < len(row) else ""
                row_active = row[active_index].lower() if active_index < len(row) else ""
                
                if (row_category == budget_data["category"].lower() and 
                    row_period == budget_data["period"].lower() and
                    row_active == "true"):
                    existing_row = i
                    break
            
            # Create a row with the exact length of headers, filled with empty strings
            row = [""] * len(headers)
            
            # Now fill in the values at the appropriate indexes
            row[amount_index] = str(budget_data["amount"])
            row[period_index] = str(budget_data["period"])
            row[category_index] = str(budget_data["category"])
            row[startdate_index] = str(budget_data["start_date"])
            row[active_index] = "TRUE"  # Explicitly use uppercase TRUE
            
            # Handle days field
            if days_index is not None:
                if budget_data["period"].lower() == "custom" and "days" in budget_data:
                    row[days_index] = str(budget_data["days"])
                elif budget_data["period"].lower() == "weekly":
                    row[days_index] = "7"
                elif budget_data["period"].lower() == "monthly":
                    row[days_index] = "30"
            
            if DEBUG:
                print(f"Row to append: {row}")
            
            # Update existing row or append new one
            if existing_row:
                # Set old budget to inactive first
                try:
                    worksheet.update_cell(existing_row, active_index + 1, "FALSE")
                    if DEBUG:
                        print(f"Set existing budget (row {existing_row}) to inactive")
                except Exception as e:
                    print(f"Error setting old budget to inactive: {str(e)}")
                    # Continue anyway
            
            # Add new budget
            try:
                worksheet.append_row(row)
                if DEBUG:
                    print("Successfully added new budget row")
            except Exception as e:
                print(f"Error appending new budget row: {str(e)}")
                return False
            
            if DEBUG:
                print("Successfully set budget in Google Sheets")
            
            return True
            
        except Exception as e:
            print(f"Error setting budget in Google Sheets: {str(e)}")
            traceback.print_exc()
            return False
    
    def get_budget(self, category=None, period=None):
        """
        Get current budget status.
        
        Args:
            category (str, optional): Category to filter by
            period (str, optional): Period to filter by ('weekly' or 'monthly')
        
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
            
            # Convert to list of dictionaries
            budgets = []
            for row in data:
                budget = dict(zip(headers, row))
                budgets.append(budget)
            
            # Filter active budgets
            active_budgets = [b for b in budgets if b.get('Active', '').lower() == 'true']
            
            # Apply category filter if provided
            if category and category.lower() != 'all':
                filtered_budgets = [b for b in active_budgets if b.get('Category') == category]
                # If no specific category budget, look for 'all' category
                if not filtered_budgets:
                    filtered_budgets = [b for b in active_budgets if b.get('Category', '').lower() == 'all']
            else:
                # Look for 'all' category budget first
                filtered_budgets = [b for b in active_budgets if b.get('Category', '').lower() == 'all']
            
            # Apply period filter if provided
            if period:
                filtered_budgets = [b for b in filtered_budgets if b.get('Period', '').lower() == period.lower()]
            
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
    
    """
Add this _date_from_str method to your SheetsService class in sheets.py
"""

    def _date_from_str(self, date_str):
        """
        Convert string date to datetime.date object.
        
        Args:
            date_str (str): Date string in YYYY-MM-DD format
            
        Returns:
            datetime.date: Converted date object or fallback date
        """
        try:
            return datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        except Exception as e:
            # Return a very old date as fallback
            if DEBUG:
                print(f"Error converting date '{date_str}': {str(e)}")
            return datetime.datetime(1970, 1, 1).date()
    