import re

with open('/Users/thilo/Library/CloudStorage/SynologyDrive-DatenSync/Repos/DAWDesk/broker/logger.py', 'r') as f:
    content = f.read()

match = re.search(r'def _log\(msg: str\):\n    print\(msg\)', content)
if match:
    replacement = """def _log(msg: str):
    print(msg)
    try:
        with open("broker.log", "a") as f:
            f.write(msg + "\\n")
    except:
        pass"""
    content = content[:match.start()] + replacement + content[match.end():]

with open('/Users/thilo/Library/CloudStorage/SynologyDrive-DatenSync/Repos/DAWDesk/broker/logger.py', 'w') as f:
    f.write(content)
