"""
Quick patch script to replace expense_service.py and openai_service.py with fixed versions.
"""
import os
import shutil

def apply_patch():
    """
    Apply patches to fix the _categories_cache issue.
    """
    # Get the directory where the script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Define source and destination paths
    expense_service_fixed = os.path.join(script_dir, "expense_service.py (Fixed)")
    openai_service_fixed = os.path.join(script_dir, "openai_service.py (Fixed)")
    
    expense_service_dest = os.path.join(script_dir, "expense_service.py")
    openai_service_dest = os.path.join(script_dir, "openai_service.py")
    
    # Back up existing files
    backup_dir = os.path.join(script_dir, "backup")
    os.makedirs(backup_dir, exist_ok=True)
    
    expense_service_backup = os.path.join(backup_dir, "expense_service.py.bak")
    openai_service_backup = os.path.join(backup_dir, "openai_service.py.bak")
    
    try:
        # Backup existing files
        if os.path.exists(expense_service_dest):
            shutil.copy2(expense_service_dest, expense_service_backup)
            print(f"Backed up expense_service.py to {expense_service_backup}")
        
        if os.path.exists(openai_service_dest):
            shutil.copy2(openai_service_dest, openai_service_backup)
            print(f"Backed up openai_service.py to {openai_service_backup}")
        
        # Copy fixed files to replace originals
        if os.path.exists(expense_service_fixed):
            shutil.copy2(expense_service_fixed, expense_service_dest)
            print(f"Applied fix to expense_service.py")
        else:
            print(f"Warning: Fixed expense_service.py not found at {expense_service_fixed}")
            
            # Apply manual patch if fixed file not found
            with open(expense_service_dest, 'r') as f:
                content = f.read()
                
            # Add import
            if "import cache_utils" not in content and "from modules import cache_utils" not in content:
                content = content.replace(
                    "from modules import category_service, sheets_service", 
                    "from modules import category_service, sheets_service, cache_utils"
                )
            
            # Replace _categories_cache reference
            content = content.replace(
                "category_service._categories_cache[\"last_updated\"] = 0", 
                "cache_utils.invalidate_cache(\"categories\")"
            )
            
            # Update fallback category
            content = content.replace("category = \"Other\"", "category = \"Miscellaneous\"")
            
            with open(expense_service_dest, 'w') as f:
                f.write(content)
                
            print("Applied manual patch to expense_service.py")
        
        if os.path.exists(openai_service_fixed):
            shutil.copy2(openai_service_fixed, openai_service_dest)
            print(f"Applied fix to openai_service.py")
        else:
            print(f"Warning: Fixed openai_service.py not found at {openai_service_fixed}")
            
            # Apply manual patch if fixed file not found
            with open(openai_service_dest, 'r') as f:
                content = f.read()
                
            # Add import
            if "import cache_utils" not in content and "from modules import cache_utils" not in content:
                content = content.replace(
                    "from modules import category_service", 
                    "from modules import category_service, cache_utils"
                )
            
            # Replace _categories_cache reference
            content = content.replace(
                "category_service._categories_cache[\"last_updated\"] = 0", 
                "cache_utils.invalidate_cache(\"categories\")"
            )
            
            # Update fallback category
            content = content.replace("category = \"Other\"", "category = \"Miscellaneous\"")
            
            with open(openai_service_dest, 'w') as f:
                f.write(content)
                
            print("Applied manual patch to openai_service.py")
        
        print("Patch completed successfully!")
        return True
    
    except Exception as e:
        print(f"Error applying patch: {str(e)}")
        # Try to restore from backup if possible
        if os.path.exists(expense_service_backup) and os.path.exists(expense_service_dest):
            shutil.copy2(expense_service_backup, expense_service_dest)
            print(f"Restored expense_service.py from backup")
            
        if os.path.exists(openai_service_backup) and os.path.exists(openai_service_dest):
            shutil.copy2(openai_service_backup, openai_service_dest)
            print(f"Restored openai_service.py from backup")
            
        return False

if __name__ == "__main__":
    apply_patch()