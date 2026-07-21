import re

with open('department_insights.py', 'r') as file:
    content = file.read()

# Define the pattern to find
pattern = r'(\ +)st\.info\(f"Using similar department name: \'([^\']+)\' instead of \'([^\']+)\'\"\)'

# Define the replacement
replacement = r'\1# Only show in debug mode\n\1if st.session_state.get(\'debug_mode\', False):\n\1    st.info(f"Using similar department name: \'\2\' instead of \'\3\'")'

# Perform the replacement
modified_content = re.sub(pattern, replacement, content)

with open('department_insights.py', 'w') as file:
    file.write(modified_content)

print("File updated successfully!")
