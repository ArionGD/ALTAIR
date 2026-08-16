import os
from fastapi.templating import Jinja2Templates

# Define templates directory relative to this file's location
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
