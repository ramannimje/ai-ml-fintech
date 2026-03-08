import sys
try:
    with open('/Users/ramannimje/Documents/Coding/github/ai-ml-fintech/app/api/routes.py', 'r') as f:
        src = f.read()
    compile(src, 'routes.py', 'exec')
    print("Syntax is VALID!")
except SyntaxError as e:
    print(f"Syntax Error: {e.msg} at line {e.lineno}")
