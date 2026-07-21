with open('department_insights.py', 'r') as file:
    lines = file.readlines()

# Fix the problematic lines
for i, line in enumerate(lines):
    if "st.session_state.get(" in line and "'" in line:
        lines[i] = line.replace("st.session_state.get('debug_mode'", "st.session_state.get(\"debug_mode\"")
    
    if "Using similar department name: '" in line:
        lines[i] = line.replace("Using similar department name: '", "Using similar department name: \"")
        lines[i] = lines[i].replace("' instead of '", "\" instead of \"")
        lines[i] = lines[i].replace("'\")", "\"\")")

with open('department_insights.py', 'w') as file:
    file.writelines(lines)

print("File updated successfully!")
