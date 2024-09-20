# history.py
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from db.session import get_db
from db.crud import create_history, get_meals_by_user_and_date
from db.models import History, Food_List, Meal_Type
from schemas.history import HistoryCreateRequest
from datetime import datetime
from api.v1.auth import validate_token
from db.models import User
import logging

logging.basicConfig(level=logging.INFO)  # DEBUG, INFO, WARNING, ERROR, CRITICAL 설정 가능
logger = logging.getLogger(__name__)


router = APIRouter()

# Decimal 타입을 float으로 변환하는 함수
def decimal_to_float(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise obj

def datetime_to_string(dt):
    """datetime 객체를 ISO 8601 문자열로 변환하는 헬퍼 함수"""
    if isinstance(dt, datetime):
        return dt.isoformat()  # datetime을 문자열로 변환
    return dt

def fix_date_format(date_str):
    """
    날짜 형식이 잘못된 경우 ':'를 '-'로 변환하여 처리.
    문자열일 경우에만 변환을 시도.
    """
    try:
        if isinstance(date_str, str):
            if ':' in date_str[:10]:  # 날짜 부분이 ':'로 구분된 경우 변환
                fixed_date = date_str.replace(':', '-', 2)  # 처음 두 개의 ':'만 '-'로 변환
                return fixed_date
        return date_str  # 이미 datetime 객체일 경우 그대로 반환
    except Exception as e:
        raise ValueError(f"Invalid date format: {str(e)}")


@router.post("/save_and_get")
def save_to_history_and_get_today_history(
    history_data: HistoryCreateRequest,  
    db: Session = Depends(get_db),
    current_user: User = Depends(validate_token)
):
    
    # current_user가 올바르게 전달되었는지 확인
    if not hasattr(current_user, 'id'):
        raise HTTPException(status_code=400, detail="Invalid user object")
    
    
    try:
        # 날짜 형식 수정
        fixed_date = fix_date_format(history_data.date)
        history_data.date = fixed_date  # 수정된 날짜를 다시 할당
    
        # 요청 받은 사용자 정보 로그 출력
        logger.info(f"current_user 확인: {current_user}, id: {current_user.id}")
        
        # 받은 요청 데이터 확인
        logger.debug(f"Received history data: {history_data}")
        
        
        # 새 기록을 데이터베이스에 저장
        new_history = create_history(
            db=db,
            current_user=current_user,
            category_id=history_data.category_id,
            meal_type_id=history_data.meal_type_id,
            image_url=history_data.image_url,
            date=history_data.date
        )
        logger.info(f"New history saved: {new_history}")


        # 기록과 음식 정보 조회
        meals = get_meals_by_user_and_date(db, current_user, history_data.date)
        logger.info(f"Meals retrieved for user {current_user.id} on {history_data.date}: {meals}")
        
        # 오늘 기록된 식사 내역이 10개 이상이면 에러 반환
        if len(meals) >= 10:
            return JSONResponse(
                {
                    "status": "Too Many Requests",
                    "status_code": 429,
                    "detail": "There are too many meal records for today."
                },
                status_code=429
            )
    

        # 응답 데이터 포맷팅
        meal_list = []
        for meal in meals:
            meal_list.append({
                "history_id": meal.history_id,
                "meal_type_name": meal.meal_type_name.encode('utf-8').decode('utf-8'),
                "category_name": meal.category_name.encode('utf-8').decode('utf-8'),
                "food_kcal": decimal_to_float(meal.food_kcal),
                "food_car": round(decimal_to_float(meal.food_car)),
                "food_prot": round(decimal_to_float(meal.food_prot)),
                "food_fat": round(decimal_to_float(meal.food_fat)),

                "date": datetime_to_string(meal.date)   # datetime을 문자열로 변환
            })
        logger.info(f"Formatted meal list for response: {meal_list}")

            
        return JSONResponse(
            content={
                "status": "success",
                "status_code": 201,  
                "detail": {
                    "Wellness_meal_list": meal_list  
                },
                "message": "meal_list information saved successfully"
            },
        media_type="application/json; charset=utf-8"  # UTF-8 인코딩을 명시적으로 설정
    )
        
    except Exception as e:
        # 저장 실패 시 에러 처리
        logger.error(f"Failed to save history: {e}")
        return JSONResponse(
            {
                "status": "Internal Server Error",
                "status_code": 500,
                "detail": "An error occurred while saving the information. The information was not saved."
            },
            status_code=500
        )


