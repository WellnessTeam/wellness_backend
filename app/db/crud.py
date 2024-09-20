# crud.py
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, DataError
from services import recommend_service
from api.v1 import recommend
from api.v1.auth import validate_token
from db.models import Food_List, Recommend, Total_Today, History, Meal_Type, User, Auth
from db import models
from sqlalchemy.sql import func
from decimal import Decimal, ROUND_HALF_UP
from datetime import date, datetime
from db import models
from schemas import UserCreate
import schemas
import logging

logger = logging.getLogger(__name__)


# 공통 예외 처리 헬퍼 함수
def execute_db_operation(db: Session, operation):
    try:
        result = operation()
        db.commit()
        return result
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Database operation failed: {str(e)}")

# 사용자의 마지막 업데이트 기록 조회
def get_user_updated_at(db: Session, current_user: models.User):
    try:
        user = db.query(models.User).filter(models.User.id == current_user.id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user.updated_at
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

# 사용자 ID로 권장 영양소 조회
def get_recommend_by_user_id(db: Session, user_id: int):
    try:
        recommend = db.query(models.Recommend).filter(models.Recommend.user_id == user_id).first()
        return recommend
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
              
# 권장 영양소 계산 및 저장(register api에 사용)
def calculate_and_save_recommendation(db: Session, user: models.User):
    recommendation_result = recommend_service.recommend_nutrition(user.weight, user.height, user.age, user.gender)
    return models.Recommend(
        user_id=user.id,
        rec_kcal=recommendation_result["rec_kcal"],
        rec_car=recommendation_result["rec_car"],
        rec_prot=recommendation_result["rec_prot"],
        rec_fat=recommendation_result["rec_fat"]
    )
    
# 사용자 권장 영양소를 조회하거나 업데이트(recommend_eaten api에 사용)
def get_or_update_recommendation(db: Session, current_user: models.User):
    try:
        # recommend 테이블에 기록 조회
        recommendation = db.query(models.Recommend).filter(models.Recommend.user_id == current_user.id).first()
        
        # 추천 정보가 없거나 사용자 정보가 최근에 업데이트된 경우
        if not recommendation or recommendation.updated_at < current_user.updated_at:
            # 새로운 추천 영양소 계산
            new_values = recommend_service.recommend_nutrition(current_user.weight, current_user.height, current_user.age, current_user.gender)
            
            if not recommendation:
                recommendation = models.Recommend(user_id=current_user.id)
                db.add(recommendation)
            # 새 값으로 recommendation 업데이트     
            recommendation.rec_kcal = new_values["rec_kcal"]
            recommendation.rec_car = new_values["rec_car"]
            recommendation.rec_prot = new_values["rec_prot"]
            recommendation.rec_fat = new_values["rec_fat"]
            recommendation.updated_at = func.now()
            
            db.commit()
            db.refresh(recommendation)

        return recommendation

    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Invalid data: Integrity constraint violated")
    except DataError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Invalid data: Data type mismatch")
    except ValueError as e: 
        raise HTTPException(status_code=400, detail=f"Invalid input: {str(e)}")
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
# 총 섭취량 조회
def get_total_today(db: Session, current_user: models.User, date_obj: date):
    try:
        logger.info(f"Checking total_today for user: {current_user.id} on date: {date_obj}")
        total_today = db.query(Total_Today).filter_by(user_id=current_user.id, today=date_obj).first()
        return total_today
    
    except SQLAlchemyError as e:
        logger.error(f"SQLAlchemyError occurred while fetching total_today: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
# 총 섭취량 생성
def create_total_today(db: Session, user_id: int, date_obj: date):
    try:
        logger.info(f"Creating total_today for user: {user_id} on date: {date_obj}")

        total_today = Total_Today(
            user_id=user_id, 
            total_kcal=Decimal('0'), 
            total_car=Decimal('0'),
            total_prot=Decimal('0'), 
            total_fat=Decimal('0'), 
            condition=False,
            created_at=func.now(), 
            updated_at=func.now(), 
            today=date_obj, 
            history_ids=[]
        )
        db.add(total_today)
        db.commit()
        db.refresh(total_today)
        return total_today
    
    except IntegrityError:
        db.rollback()
        logger.error("IntegrityError occurred while creating total_today")
        raise HTTPException(status_code=400, detail="Invalid data: Integrity constraint violated")
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"SQLAlchemyError occurred: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


# Total_Today 업데이트
def update_total_today(db: Session, total_today: models.Total_Today):
    try:
        # 최대 허용 범위에 맞춰 값 제한
        max_value = Decimal('9999.99')
        total_today.total_kcal = min(total_today.total_kcal, max_value)
        total_today.total_car = min(total_today.total_car, max_value)
        total_today.total_prot = min(total_today.total_prot, max_value)
        total_today.total_fat = min(total_today.total_fat, max_value)
        
        # condition 값이 없을 경우 False로 설정
        if total_today.condition is None:
            total_today.condition = False
        
        db.refresh(total_today)
        db.commit()
        return total_today
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update Total_Today: {str(e)}")


def get_food_by_category(db: Session, category_id: int) -> Food_List:
     food_item = db.query(Food_List).filter(Food_List.category_id == category_id).first()
     
     if not food_item:
          raise HTTPException(status_code=404, detail="Food category not found")
     
     return food_item


def get_recommend_by_user(db: Session, currnet_user: models.User) -> Recommend:
     Recommendation = db.query(Recommend).filter(Recommend.user_id == currnet_user.id).first()
     
     if not Recommendation:
          raise HTTPException(status_code=400, detail="Recommendation not found")
     
     return Recommendation

# history 저장 함수 
def create_history(db: Session, current_user: models.User, category_id: int, meal_type_id: int, image_url: str, date: date):
    # current_user가 User 객체인지 확인
    if not hasattr(current_user, 'id'):
        logger.error(f"current_user가 User 객체가 아님: {current_user}")
        raise HTTPException(status_code=400, detail="Invalid user object")
    
    new_history = History(
        user_id=current_user.id,
        category_id=category_id,
        meal_type_id=meal_type_id,
        image_url=image_url,
        date=date
    )
    db.add(new_history)
    db.commit()
    db.refresh(new_history)
    logger.info(f"new_history 저장됨: {new_history}")
    return new_history

# meals 조회 함수
def get_meals_by_user_and_date(db: Session, current_user: models.User, date: datetime):
    logger.info(f"get_meals_by_user_and_date 호출됨, user_id: {current_user.id}, date: {date}")
    return db.query(
        History.id.label("history_id"),
        Meal_Type.type_name.label("meal_type_name"),
        Food_List.category_name,
        Food_List.food_kcal,
        Food_List.food_car,
        Food_List.food_prot,
        Food_List.food_fat,
        History.date
    ).join(Food_List, History.category_id == Food_List.category_id) \
     .join(Meal_Type, History.meal_type_id == Meal_Type.id) \
     .filter(History.date == date) \
     .filter(History.user_id == current_user.id) \
     .all()

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

# 사용자 생성
def create_user(db: Session, user: schemas.UserCreate, age: int):
    db_user = models.User(
        birthday=user.birthday,
        age=age,
        gender=user.gender,
        nickname=user.nickname,
        height=user.height,
        weight=user.weight,
        email=user.email
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


# total_today condition 업데이트
def update_total_today_condition(db: Session, total_today_id: int, new_condition: bool):
    try:
        total_today = db.query(models.Total_Today).filter(models.Total_Today.id == total_today_id).first()
        if total_today:
            # 사용자 권장 영양소 가져오기
            recommendation = db.query(models.Recommend).filter(models.Recommend.user_id == total_today.user_id).first()

            if recommendation:
                # 새로운 condition 계산
                new_condition = total_today.total_kcal > recommendation.rec_kcal
                # 현재 condition과 새로운 condition이 다를 경우에만 db 업데이트
                if total_today.condition != new_condition:
                    total_today.condition = new_condition
                    db.commit() 
                    db.refresh(total_today)  
        
        return total_today

    except SQLAlchemyError as e:
        db.rollback()  
        print(f"Database error occurred: {e}")
        return None

    except Exception as e:
        db.rollback()  
        print(f"An unexpected error occurred: {e}")
        return None
    
# 만 나이 계산 함수 추가(create_user에서 사용)
def calculate_age(birth_date) -> int:
    today = date.today()
    age = today.year - birth_date.year

    # 생일 지나지 않은 경우 나이 - 1
    if(today.month, today.day) < (birth_date.month, birth_date.day):
        age -= 1
    
    return age

