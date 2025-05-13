import os
from dotenv import load_dotenv

load_dotenv()

# Use SQLite database
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///urls.db') 