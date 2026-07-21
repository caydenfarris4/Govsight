"""
Script to fix the forecast display issue in bi_sandbox.py
"""

import os
import re

# File path
file_path = 'bi_sandbox.py'

# Read the original file
with open(file_path, 'r') as file:
    content = file.read()

# Replace all occurrences of the raw variable with session state
# Pattern looks for 'forecast_data_in_session and show_forecast_on_chart'
pattern = r'forecast_data_in_session and show_forecast_on_chart'
replacement = r'forecast_data_in_session and st.session_state.show_forecast_on_chart'

# Perform the replacement
new_content = re.sub(pattern, replacement, content)

# Write back to the file
with open(file_path, 'w') as file:
    file.write(new_content)

print("Replacement complete. All instances of 'show_forecast_on_chart' should now use session state.")