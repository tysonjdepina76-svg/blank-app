import os
from dotenv import load_dotenv

# Load local .env when running on your device
load_dotenv()

SPORTSDATAIO_API_KEY = os.getenv("SPORTSDATAIO_API_KEY")
DVOA_API_KEY = os.getenv("DVOA_API_KEY")
INJURY_API_KEY = os.getenv("INJURY_API_KEY")
ADVANCED_METRICS_API_KEY = os.getenv("ADVANCED_METRICS_API_KEY")