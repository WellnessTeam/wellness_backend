from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from jose import jwt, JWTError
from schemas.user import UserLogin
from db.session import get_db
from db.models import Auth, User
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import logging

# .env 파일 로드
load_dotenv()

# 환경 변수 로드
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS"))

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# 날짜 및 시간 형식을 'YYYY-MM-DD HH:MM:SS'로 포맷
def format_datetime(dt: datetime):
    return dt.strftime("%Y-%m-%d %H:%M:%S")

# Access 토큰 생성
def create_access_token(data: dict, expires_delta: int):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=expires_delta)
    to_encode.update({"exp": expire})
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    logger.info(f"Access Token 생성 완료: {token}")
    return token

# 리프레시 토큰 생성
def create_refresh_token(data: dict, expires_delta: int):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=expires_delta)
    to_encode.update({"exp": expire})
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    logger.info(f"Refresh Token 생성 완료: {token}")
    return token

# 엑세스 토큰 만료 확인 함수
def is_access_token_expired(expiry_time: datetime):
    return datetime.utcnow() > expiry_time

# 토큰 검증 함수
def verify_refresh_token(token: str, expiry_time: datetime):
    if datetime.utcnow() > expiry_time:
        logger.error("Refresh token expired based on expiry_time in DB")
        raise HTTPException(status_code=401, detail="Refresh token expired")
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        logger.info(f"Refresh Token validated successfully: {payload}")
        return payload
    except JWTError as e:   
        logger.error(f"Refresh token validation failed: {e}")
        raise HTTPException(
            status_code=401, detail="Refresh token invalid or expired")

@router.post("/login")
async def login(user: UserLogin, db: Session = Depends(get_db)):
    logger.info(f"로그인 시도: {user.email}, {user.nickname}")

    # 사용자 확인
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        logger.info(f"DB User found: {db_user.email}, ID: {db_user.id}")
    else:
        logger.error(f"DB User not found: {user.email}")
        raise HTTPException(status_code=400, detail="User not found")

    # auth 테이블에서 사용자 토큰 확인
    auth_entry = db.query(Auth).filter(Auth.user_id == db_user.id).first()

    if auth_entry:
        # 엑세스 토큰 만료 확인
        if is_access_token_expired(auth_entry.access_expired_at):
            try:
                # refresh 토큰 검증
                verify_refresh_token(auth_entry.refresh_token, auth_entry.refresh_expired_at)

                # refresh 토큰이 유효하므로 access 토큰만 재발급
                access_token = create_access_token(
                    data={"user_id": db_user.id, "user_email": db_user.email},
                    expires_delta=ACCESS_TOKEN_EXPIRE_MINUTES
                )
                auth_entry.access_token = access_token
                auth_entry.access_created_at = format_datetime(datetime.utcnow())
                auth_entry.access_expired_at = format_datetime(
                    datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
                )
                logger.info(f"access_created_at: {auth_entry.access_created_at}, access_expired_at: {auth_entry.access_expired_at}")
                
                try:
                    db.commit()
                    
                except SQLAlchemyError as e:
                    db.rollback()
                    logger.error(f"failed to commit to DB: {e}")
                    raise HTTPException(status_code=500, detail="Failed to issue new token")
                    
                return {
                    "status": "success",
                    "status_code": 200,
                    "detail": {
                        "wellness_info": {
                            "access_token": auth_entry.access_token,
                            "refresh_token": auth_entry.refresh_token,  # refresh 토큰은 유지
                            "token_type": "bearer",
                            "user_email": db_user.email,
                            "user_nickname": db_user.nickname,
                            "user_birthday": db_user.birthday,
                            "user_gender": db_user.gender,
                            "user_height": db_user.height,
                            "user_weight": db_user.weight,
                            "user_age": db_user.age,
                        }
                    },
                    "message": "Access token renewed."
                }

            except HTTPException:
                # 엑세스 토큰과 리프레시 토큰이 모두 만료된 경우 새로 발급
                access_token = create_access_token(
                    data={"user_id": db_user.id, "user_email": db_user.email},
                    expires_delta=ACCESS_TOKEN_EXPIRE_MINUTES
                )
                refresh_token = create_refresh_token(
                    data={"user_id": db_user.id, "user_email": db_user.email},
                    expires_delta=REFRESH_TOKEN_EXPIRE_DAYS
                )

                # auth 테이블에 새 토큰 저장
                new_auth_entry = Auth(
                    user_id=db_user.id,
                    access_token=access_token,
                    refresh_token=refresh_token,
                    access_created_at=format_datetime(datetime.utcnow()),
                    access_expired_at=format_datetime(
                        datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
                    ),
                    refresh_created_at=format_datetime(datetime.utcnow()),
                    refresh_expired_at=format_datetime(
                        datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
                    ),
                )
                db.add(new_auth_entry)
                db.commit()

                logger.info(f"Committing new auth entry for user_id {db_user.id}")
                return {
                    "status": "success",
                    "status_code": 201,
                    "detail": {
                        "wellness_info": {
                            "access_token": new_auth_entry.access_token,
                            "refresh_token": new_auth_entry.refresh_token,
                            "token_type": "bearer",
                            "user_email": db_user.email,
                            "user_nickname": db_user.nickname,
                            "user_birthday": db_user.birthday,
                            "user_gender": db_user.gender,
                            "user_height": db_user.height,
                            "user_weight": db_user.weight,
                            "user_age": db_user.age,
                        }
                    },
                    "message": "New access and refresh tokens issued."
                }

        else:
            # 엑세스 토큰이 아직 유효한 경우
            logger.info(f"Valid access token found for user_id: {db_user.id}")
            return {
                "status": "success",
                "status_code": 200,
                "detail": {
                    "wellness_info": {
                        "access_token": auth_entry.access_token,
                        "refresh_token": auth_entry.refresh_token,
                        "token_type": "bearer",
                        "user_email": db_user.email,
                        "user_nickname": db_user.nickname,
                        "user_birthday": db_user.birthday,
                        "user_gender": db_user.gender,
                        "user_height": db_user.height,
                        "user_weight": db_user.weight,
                        "user_age": db_user.age,
                    }
                },
                "message": "Existing token provided."
            }

    else:
        logger.error(f"No auth entry found for user_id: {db_user.id}")
        raise HTTPException(status_code=400, detail="No auth entry found.")
