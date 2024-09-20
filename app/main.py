# /app/main.py
from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.security import OAuth2PasswordBearer
from requests import session
from api.v1 import recommend, model, register, oauth, login
from api.v1.auth import validate_token
from db import models
from db.session import get_db
from db.models import Auth
from api.v1.history import router as history_router
import logging
import os
import time

# 로그 설정
log_file_path = os.path.join(os.getcwd(), "app.log")

logging.basicConfig(
    level=logging.INFO,  # 로그 레벨 설정
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file_path),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# fastapi 앱 생성
app = FastAPI()

# 요청 및 응답을 기록하는 미들웨어 추가
@app.middleware("http")
async def log_requests(request: Request, call_next):
    # 요청 정보 기록
    logger.info(f"Incoming request: {request.method} {request.url}")
    
    # 요청 처리 시간 측정
    start_time = time.time()
    
    # 요청을 처리하여 응답 생성
    response = await call_next(request)
    
    # 처리 완료 후, 응답 시간 기록
    duration = time.time() - start_time
    logger.info(f"Completed request in {duration:.2f}s - Status Code: {response.status_code}")
    
    return response

# 전역 예외 처리: HTTP 예외 처리
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    logger.error(f"HTTP Exception: {exc.detail} - Request URL: {request.url}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

# 전역 예외 처리: 유효성 검사 처리
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(f"Validation Error: {exc.errors()} - Request URL: {request.url}")
    return JSONResponse(
        status_code=400,
        content={"detail": exc.errors()},
    )

# api 라우터 설정
app.include_router(oauth.router, prefix="/api/v1/oauth", tags=["Oauth_kakaotoken"])
app.include_router(login.router, prefix="/api/v1/user", tags=["user_Login"])
app.include_router(register.router, prefix="/api/v1/user", tags=["user_Register"])
app.include_router(recommend.router, prefix="/api/v1/recommend", tags=["Recommend"], dependencies=[Depends(validate_token)])
app.include_router(model.router, prefix="/api/v1/model", tags=["Model"], dependencies=[Depends(validate_token)])
app.include_router(history_router, prefix="/api/v1/history", tags=["History"], dependencies=[Depends(validate_token)])

# 서버 시작 시 로그 출력
logger.info("FastAPI application has started.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
