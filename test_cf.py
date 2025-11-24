import json
from types import SimpleNamespace

# Mock request object similar to Flask request
class MockRequest:
    def __init__(self, json_body=None, args=None):
        self._json = json_body
        self.args = args or {}
    def get_json(self, silent=False):
        return self._json

# Import the cloud function entry point
from main import cloud_function_entry

# Create request with action=recreate_table
request = MockRequest(json_body={"action": "recreate_table"})

# Call the function
response = cloud_function_entry(request)
print("Response:", response)
