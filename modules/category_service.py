"""
Category management service for the financial tracker.
This module handles creating, reading, updating, and deleting expense categories.
"""
import os
from modules import sheets_service, cache_utils
from config import SHEET_ID

# Sheet name for categories
CATEGORIES_SHEET = "Categories"

def ensure_categories_sheet():
    """
    Ensure that the Categories sheet exists in the spreadsheet.
    Creates it with default categories if it doesn't exist.
    """
    try:
        # Try to get from cache first
        categories = cache_utils.get_cached("categories")
        if categories:
            print("Using cached categories")
            return True
            
        # Get the client
        client = sheets_service.get_sheets_client()
        
        # Open the spreadsheet by ID
        spreadsheet = client.open_by_key(SHEET_ID)
        
        # Check if Categories sheet exists
        sheet_exists = False
        for sheet in spreadsheet.worksheets():
            if sheet.title == CATEGORIES_SHEET:
                sheet_exists = True
                break
                
        if sheet_exists:
            print(f"{CATEGORIES_SHEET} sheet exists")
        else:
            # Create the sheet with default categories
            print(f"Creating {CATEGORIES_SHEET} sheet")
            categories_sheet = spreadsheet.add_worksheet(
                title=CATEGORIES_SHEET, 
                rows=20, 
                cols=2
            )
            
            # Add headers
            categories_sheet.update('A1:B1', [['Category', 'Description']])
            
            # Add default categories
            default_categories = [
                ["Food", "Groceries, restaurants, takeout"],
                ["Transport", "Public transit, gas"],
                ["Transportation", "Ride services, taxis, commuting"],
                ["Entertainment", "Movies, games, hobbies"],
                ["Shopping", "Clothing, electronics, gifts"],
                ["Utilities", "Electricity, water, internet"],
                ["Housing", "Rent, mortgage, repairs"],
                ["Health", "Medical bills, pharmacy"],
                ["Education", "Tuition, books, courses"],
                ["Other", "Miscellaneous expenses"]
            ]
            categories_sheet.update('A2:B11', default_categories)
            
        # Get the categories to cache them
        categories_sheet = spreadsheet.worksheet(CATEGORIES_SHEET)
        categories = categories_sheet.col_values(1)[1:]
        cache_utils.set_cached("categories", categories)
        
        return True
        
    except Exception as e:
        print(f"Error ensuring categories sheet: {str(e)}")
        # Don't crash the whole app - use default categories
        default_categories = ["Food", "Transport", "Transportation", "Entertainment", 
                             "Shopping", "Utilities", "Housing", "Health", 
                             "Education", "Other"]
        cache_utils.set_cached("categories", default_categories)
        return False

def get_categories():
    """
    Get all categories from the Categories sheet.
    
    Returns:
        list: List of category names
    """
    try:
        # Define fetch function for cache
        def fetch_categories():
            # Ensure the sheet exists first
            ensure_categories_sheet()
            
            # If that doesn't populate cache, fetch directly
            client = sheets_service.get_sheets_client()
            spreadsheet = client.open_by_key(SHEET_ID)
            categories_sheet = spreadsheet.worksheet(CATEGORIES_SHEET)
            categories = categories_sheet.col_values(1)[1:]
            return categories
            
        # Try to get from cache, or fetch if needed
        categories = cache_utils.get_cached("categories", ttl=60, fetch_func=fetch_categories)
        
        # Debug output
        print(f"Retrieved categories: {categories}")
        
        return categories
        
    except Exception as e:
        print(f"Error getting categories: {str(e)}")
        # Return default categories instead of raising an exception
        default_categories = ["Food", "Transport", "Transportation", "Entertainment", 
                             "Shopping", "Utilities", "Housing", "Health", 
                             "Education", "Other"]
        print("Using default categories as fallback")
        
        # Update cache with defaults to prevent repeated API calls
        cache_utils.set_cached("categories", default_categories)
        
        return default_categories

def add_category(name, description=""):
    """
    Add a new category to the Categories sheet.
    
    Args:
        name (str): Name of the category
        description (str, optional): Description of the category
        
    Returns:
        bool: True if successful
    """
    try:
        # Get current categories (use cache if available)
        current_categories = get_categories()
        
        # Check if category already exists
        if name in current_categories:
            raise ValueError(f"Category '{name}' already exists")
        
        # Get the client
        client = sheets_service.get_sheets_client()
        
        # Open the spreadsheet
        spreadsheet = client.open_by_key(SHEET_ID)
        
        # Get the categories sheet
        categories_sheet = spreadsheet.worksheet(CATEGORIES_SHEET)
        
        # Append the new category
        categories_sheet.append_row([name, description])
        
        # Update the cache with the new category
        current_categories.append(name)
        cache_utils.set_cached("categories", current_categories)
        
        return True
        
    except Exception as e:
        print(f"Error adding category: {str(e)}")
        raise Exception(f"Failed to add category: {str(e)}")

def rename_category(old_name, new_name):
    """
    Rename an existing category.
    
    Args:
        old_name (str): Current name of the category
        new_name (str): New name for the category
        
    Returns:
        bool: True if successful
    """
    try:
        # Get current categories (use cache if available)
        current_categories = get_categories()
        
        # Check if old category exists
        if old_name not in current_categories:
            raise ValueError(f"Category '{old_name}' does not exist")
            
        # Check if new category already exists
        if new_name in current_categories and old_name != new_name:
            raise ValueError(f"Category '{new_name}' already exists")
        
        # Get the client
        client = sheets_service.get_sheets_client()
        
        # Open the spreadsheet
        spreadsheet = client.open_by_key(SHEET_ID)
        
        # Get the categories sheet
        categories_sheet = spreadsheet.worksheet(CATEGORIES_SHEET)
        
        # Find the row with the old category name
        cell = categories_sheet.find(old_name)
        
        if cell:
            # Update the cell with the new name
            categories_sheet.update_cell(cell.row, cell.col, new_name)
            
            # Also update all expenses with this category
            update_existing_expenses(old_name, new_name)
            
            # Update the cache
            updated_categories = [new_name if cat == old_name else cat for cat in current_categories]
            cache_utils.set_cached("categories", updated_categories)
            
            return True
        else:
            raise ValueError(f"Category '{old_name}' not found in sheet")
        
    except Exception as e:
        print(f"Error renaming category: {str(e)}")
        raise Exception(f"Failed to rename category: {str(e)}")

def delete_category(name):
    """
    Delete a category.
    
    Args:
        name (str): Name of the category to delete
        
    Returns:
        bool: True if successful
    """
    try:
        # Prevent deleting "Other" category as it's the fallback
        if name.lower() == "other":
            raise ValueError("Cannot delete the 'Other' category as it's required")
        
        # Get current categories (use cache if available)
        current_categories = get_categories()
        
        # Check if category exists
        if name not in current_categories:
            raise ValueError(f"Category '{name}' does not exist")
        
        # Get the client
        client = sheets_service.get_sheets_client()
        
        # Open the spreadsheet
        spreadsheet = client.open_by_key(SHEET_ID)
        
        # Get the categories sheet
        categories_sheet = spreadsheet.worksheet(CATEGORIES_SHEET)
        
        # Find the row with the category name
        cell = categories_sheet.find(name)
        
        if cell:
            # Delete the row
            categories_sheet.delete_rows(cell.row)
            
            # Update existing expenses to use "Other" category
            update_existing_expenses(name, "Other")
            
            # Update the cache
            updated_categories = [cat for cat in current_categories if cat != name]
            cache_utils.set_cached("categories", updated_categories)
            
            return True
        else:
            raise ValueError(f"Category '{name}' not found in sheet")
        
    except Exception as e:
        print(f"Error deleting category: {str(e)}")
        raise Exception(f"Failed to delete category: {str(e)}")

def update_existing_expenses(old_category, new_category):
    """
    Update all expenses that use old_category to use new_category.
    
    Args:
        old_category (str): The category being replaced
        new_category (str): The category to replace with
        
    Returns:
        int: Number of expenses updated
    """
    try:
        # Get the client
        client = sheets_service.get_sheets_client()
        
        # Open the spreadsheet
        spreadsheet = client.open_by_key(SHEET_ID)
        
        # Get the expenses sheet
        expenses_sheet = spreadsheet.worksheet("Expenses")
        
        # Find all cells with the old category
        cells = expenses_sheet.findall(old_category)
        
        # Update each cell
        count = 0
        for cell in cells:
            # Make sure we're updating the Category column (assumed to be column 4)
            if cell.col == 4:  # Assuming Category is in column D (4)
                expenses_sheet.update_cell(cell.row, cell.col, new_category)
                count += 1
        
        return count
        
    except Exception as e:
        print(f"Error updating existing expenses: {str(e)}")
        raise Exception(f"Failed to update expenses: {str(e)}")