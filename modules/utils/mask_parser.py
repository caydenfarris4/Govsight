# mask_parser.py
import json
import os

SETTINGS_FILE = "system_settings.json"

def get_mask_from_settings(account_type: str) -> str:
    """Returns the appropriate mask from system settings based on type."""
    if not os.path.exists(SETTINGS_FILE):
        return ""
    with open(SETTINGS_FILE, "r") as f:
        settings = json.load(f)
    return settings.get(f"Mask_{account_type}", "")

def parse_account(account_str: str, mask: str) -> dict:
    """Parses an account string based on a given mask like 'FF-DD-OOOO'"""
    clean_mask = mask.replace("-", "")
    segment_map = {}
    mask_parts = mask.split("-")
    
    index = 0
    for part in mask_parts:
        label = {
            'F': 'Fund',
            'D': 'Dept',
            'O': 'Object',
            'C': 'Category',
            'A': 'Account',
            'B': 'SubFund'
        }.get(part[0], f"Part{index}")
        
        length = len(part)
        segment = account_str[index:index+length]
        segment_map[label] = segment
        index += length
    
    return segment_map

# Example usage
if __name__ == "__main__":
    mask = "FF-DD-OOOO"
    account = "10304012"
    result = parse_account(account, mask)
    print(result)