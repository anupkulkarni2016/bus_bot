from dotenv import load_dotenv
import os

load_dotenv()

print("API KEY:", os.getenv("GOOGLE_MAPS_API_KEY"))
print("HOME:", os.getenv("HOME_ADDRESS"))
print("WORK:", os.getenv("DEFAULT_WORK_ADDRESS"))