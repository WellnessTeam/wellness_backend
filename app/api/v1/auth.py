from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError
from db.session import get_db
from db.models import Auth, User
from schemas.auth import Token, TokenData
import logging
import os

# 환경 변수에서 비밀 키와 알고리즘 불러오기
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # 엑세스 토큰 만료 시간 (분)
REFRESH_TOKEN_EXPIRE_DAYS = 7  # 리프레시 토큰 만료 시간 (일)

router = APIRouter()

# 토큰을 Bearer 방식으로 받아오는 OAuth2 스키마
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# 로깅 설정
logger = logging.getLogger(__name__)



async def validate_token(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    # 토큰을 확인하는 로그 추가
    logger.info(f"Received token: {token}")

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # 데이터베이스에서 토큰 조회
    auth_entry = db.query(Auth).filter(Auth.access_token == token).first()
    
    if auth_entry is None:
        # 토큰 조회 실패 시 로그 기록
        logger.error(f"Token not found in the database: {token}")
        raise credentials_exception

    # 토큰 만료 여부 확인
    if auth_entry.access_expired_at < datetime.utcnow():
        # 만료된 토큰일 경우 로그 기록
        logger.error(f"Token expired: {token}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 여기서 User 객체 반환
    user = db.query(User).filter(User.id == auth_entry.user_id).first()
    if user is None:
        logger.error(f"User not found for token: {token}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.info(f"Returning user object: {user} of type {type(user)}")
    return user