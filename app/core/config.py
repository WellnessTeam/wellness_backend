# /app/core/config.py
import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# 환경 변수들 설정
DATABASE_URL = os.getenv("DATABASE_URL")
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
bucket_name = os.getenv("BUCKET_NAME") 
