with open('department_insights.py', 'r') as file:
    content = file.read()

# Replace all remaining instances of escaped quotes
content = content.replace("\\\'", "'")
content = content.replace("\\\"", "\"")

with open('department_insights.py', 'w') as file:
    file.write(content)

print("Quotes fixed successfully!")
