"""
Preference management service for the financial tracker.
This module handles storing and retrieving user preferences.
"""
import time
from modules import sheets_service
from config import SHEET_ID

# Sheet name for preferences
PREFERENCES_SHEET = "Preferences"

# Cache for preferences to reduce API calls
_preferences_cache = {
    "preferences": {},
    "last_updated": 0,
    "cache_ttl": 60  # Cache time-to-live in seconds
}

def _is_cache_valid():
    """Check if the cache is valid."""
    cache_age = time.time() - _preferences_cache["last_updated"]
    return cache_age < _preferences_cache["cache_ttl"]

def _update_cache(preferences):
    """Update the preferences cache."""
    _preferences_cache["preferences"] = preferences
    _preferences_cache["last_updated"] = time.time()

def ensure_preferences_sheet():
    """
    Ensure that the Preferences sheet exists in the spreadsheet.
    Creates it if it doesn't exist.
    """
    try:
        # Get the client
        client = sheets_service.get_sheets_client()
        
        # Open the spreadsheet by ID
        spreadsheet = client.open_by_key(SHEET_ID)
        
        # Check if Preferences sheet exists
        sheet_exists = False
        for sheet in spreadsheet.worksheets():
            if sheet.title == PREFERENCES_SHEET:
                sheet_exists = True
                break
                
        if sheet_exists:
            print(f"{PREFERENCES_SHEET} sheet exists")
        else:
            # Create the sheet
            print(f"Creating {PREFERENCES_SHEET} sheet")
            preferences_sheet = spreadsheet.add_worksheet(
                title=PREFERENCES_SHEET, 
                rows=20, 
                cols=3
            )
            
            # Add headers
            preferences_sheet.update('A1:C1', [['UserID', 'Setting', 'Value']])
            
        return True
        
    except Exception as e:
        print(f"Error ensuring preferences sheet: {str(e)}")
        return False

def get_user_preferences(user_id):
    """
    Get all preferences for a user.
    
    Args:
        user_id: User's Telegram ID
        
    Returns:
        dict: Dictionary of user preferences
    """
    try:
        # Check if cache is valid
        if _is_cache_valid() and user_id in _preferences_cache["preferences"]:
            return _preferences_cache["preferences"][user_id]
            
        # Ensure the sheet exists
        ensure_preferences_sheet()
        
        # Get the client
        client = sheets_service.get_sheets_client()
        
        # Open the spreadsheet
        spreadsheet = client.open_by_key(SHEET_ID)
        
        # Get the preferences sheet
        preferences_sheet = spreadsheet.worksheet(PREFERENCES_SHEET)
        
        # Get all values
        data = preferences_sheet.get_all_values()
        
        # Skip header row
        if len(data) <= 1:
            # No preferences yet
            return {}
            
        # Convert to dictionary of user preferences
        all_preferences = {}
        
        for row in data[1:]:
            if len(row) >= 3:
                row_user_id = str(row[0])
                setting = row[1]
                value = row[2]
                
                # Initialize user dict if needed
                if row_user_id not in all_preferences:
                    all_preferences[row_user_id] = {}
                    
                # Store the preference
                all_preferences[row_user_id][setting] = value
        
        # Update cache
        _update_cache(all_preferences)
        
        # Return the user's preferences
        return all_preferences.get(str(user_id), {})
        
    except Exception as e:
        print(f"Error getting user preferences: {str(e)}")
        return {}

def get_user_preference(user_id, setting, default_value=None):
    """
    Get a specific preference for a user.
    
    Args:
        user_id: User's Telegram ID
        setting: The preference name
        default_value: Default value if preference not found
        
    Returns:
        The preference value or default
    """
    preferences = get_user_preferences(user_id)
    value = preferences.get(setting, default_value)
    
    # Attempt to convert to appropriate type
    if default_value is not None:
        try:
            if isinstance(default_value, int):
                return int(value)
            elif isinstance(default_value, float):
                return float(value)
            elif isinstance(default_value, bool):
                return value.lower() == 'true'
        except (ValueError, TypeError):
            return default_value
            
    return value

def set_user_preference(user_id, setting, value):
    """
    Set a preference for a user.
    
    Args:
        user_id: User's Telegram ID
        setting: The preference name
        value: The preference value
        
    Returns:
        bool: True if successful
    """
    try:
        # Ensure the sheet exists
        ensure_preferences_sheet()
        
        # Get the client
        client = sheets_service.get_sheets_client()
        
        # Open the spreadsheet
        spreadsheet = client.open_by_key(SHEET_ID)
        
        # Get the preferences sheet
        preferences_sheet = spreadsheet.worksheet(PREFERENCES_SHEET)
        
        # Get existing preferences to check if this is an update
        existing_preferences = get_user_preferences(user_id)
        
        # Convert user_id and value to strings for storage
        user_id_str = str(user_id)
        value_str = str(value)
        
        # Check if this preference already exists
        if setting in existing_preferences:
            # Find the row to update
            all_data = preferences_sheet.get_all_values()
            
            for i, row in enumerate(all_data):
                if (i > 0 and  # Skip header
                    len(row) >= 3 and
                    str(row[0]) == user_id_str and
                    row[1] == setting):
                    
                    # Update value
                    preferences_sheet.update_cell(i + 1, 3, value_str)
                    break
            else:
                # Not found, add new row
                preferences_sheet.append_row([user_id_str, setting, value_str])
        else:
            # Add new preference
            preferences_sheet.append_row([user_id_str, setting, value_str])
            
        # Update cache
        if _is_cache_valid():
            if user_id_str not in _preferences_cache["preferences"]:
                _preferences_cache["preferences"][user_id_str] = {}
                
            _preferences_cache["preferences"][user_id_str][setting] = value_str
            
        return True
        
    except Exception as e:
        print(f"Error setting user preference: {str(e)}")
        return False

# Week start day specific functions
def get_week_start_day(user_id):
    """
    Get user's preferred week start day.
    
    Args:
        user_id: User's Telegram ID
        
    Returns:
        int: Day index (0=Monday, 6=Sunday), defaults to 0 (Monday)
    """
    return get_user_preference(user_id, "week_start_day", 0)

def set_week_start_day(user_id, day_index):
    """
    Set user's preferred week start day.
    
    Args:
        user_id: User's Telegram ID
        day_index: Day index (0=Monday, 6=Sunday)
        
    Returns:
        bool: True if successful
    """
    # Validate day index
    if not (0 <= day_index <= 6):
        print(f"Invalid day index: {day_index}")
        return False
        
    return set_user_preference(user_id, "week_start_day", day_index)