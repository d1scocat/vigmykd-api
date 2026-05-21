import os
import dotenv


dotenv.load_dotenv()


BASE_URL=os.getenv("BASE_URL")
REG_CONFIRM_CODE_TTL = int(os.getenv("REG_CODE_TTL"))