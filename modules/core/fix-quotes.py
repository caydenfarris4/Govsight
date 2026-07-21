import re

with open('department_insights.py', 'r') as file:
    content = file.read()

# Replace escaped quotes in the modified lines
content = content.replace("st.session_state.get(\'debug_mode\'", "st.session_state.get('debug_mode'")
content = content.replace("st.info(f\"Using similar department name: \'", "st.info(f\"Using similar department name: '")
content = content.replace("\' instead of \'", "' instead of '")
content = content.replace("\'\")", "'\")")

with open('department_insights.py', 'w') as file:
    file.write(content)

print("Quotes fixed successfully!")
