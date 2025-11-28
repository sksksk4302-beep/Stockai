from main import cloud_function_entry

class MockRequest:
    def get_json(self, silent=True): return None
    @property
    def args(self): return {}
    @property
    def path(self): return "/"

if __name__ == "__main__":
    print("Starting batch processing...")
    cloud_function_entry(MockRequest())
