# /app/services/recommend_service.py
from sqlalchemy.orm import Session
from db import crud, models
from fastapi import HTTPException
from decimal import Decimal, ROUND_HALF_UP

# def recommend_nutrition(user_id: int, db: Session):
#     try:
#         user = db.query(models.User).filter(models.User.id == user_id).first()

#         if not user:
#             raise HTTPException(
#                 detail={"status": "error", "message": "Invalid user_id"}
#             )
        
#         # 기존 권장 영양소 정보 조회
#         existing_recommendation = db.query(models.Recommend).filter(models.Recommend.user_id == user_id).first()
        
#         # 사용자 정보가 업데이트되었거나 권장 영양소 정보가 없는 경우에만 새로 계산
#         if existing_recommendation is None or existing_recommendation.updated_at < user.updated_at:
#             # BMR 계산 (해리스-베네딕트 방정식 사용)
#             if user.gender == 0:  # 남성일 경우
#                 bmr = Decimal('88.362') + (Decimal('13.397') * user.weight) + (Decimal('4.799') * Decimal(str(user.height))) - (Decimal('5.677') * Decimal(str(user.age)))
#             else:  # 여성이거나 다른 경우
#                 bmr = Decimal('447.593') + (Decimal('9.247') * user.weight) + (Decimal('3.098') * Decimal(str(user.height))) - (Decimal('4.330') * Decimal(str(user.age)))

#             rec_kcal = bmr * Decimal('1.55')  # 보통 활동량

#             # 탄, 단, 지 비율 설정 5:3:2
#             rec_car = (rec_kcal * Decimal('0.5')) / Decimal('4')  # 1g 4kcal
#             rec_prot = (rec_kcal * Decimal('0.3')) / Decimal('4')  # 1g 4kcal
#             rec_fat = (rec_kcal * Decimal('0.2')) / Decimal('9')  # 1g 9kcal

#             rec_kcal = rec_kcal.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
#             rec_car = rec_car.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
#             rec_prot = rec_prot.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
#             rec_fat = rec_fat.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

#             # 데이터베이스에 저장 또는 업데이트
#             recommendation = crud.get_or_update_recommendation(db, user_id, rec_kcal, rec_car, rec_prot, rec_fat)
#         else:
#             # 기존 권장 영양소 정보 사용
#             recommendation = existing_recommendation

#         return {
#             "status": "success",
#             "rec_kcal": recommendation.rec_kcal,
#             "rec_car": recommendation.rec_car,
#             "rec_prot": recommendation.rec_prot,
#             "rec_fat": recommendation.rec_fat,
#             "updated_at": recommendation.updated_at
#         }

#     except HTTPException as http_ex:
#         raise http_ex
#     except Exception as e:
#         raise HTTPException(
#             detail={"status": "error", "message": "Internal server error. Please try again later."}
#         )
def recommend_nutrition(weight: Decimal, height: Decimal, age: int, gender: int):
    if weight <= 0 or height <= 0 or age <= 0 or gender not in [0, 1]:
        raise ValueError("Invalid input parameters")

    if gender == 0:  # 남성일 경우
        bmr = Decimal('88.362') + (Decimal('13.397') * weight) + (Decimal('4.799') * height) - (Decimal('5.677') * Decimal(str(age)))
    else:  # 여성이거나 다른 경우
        bmr = Decimal('447.593') + (Decimal('9.247') * weight) + (Decimal('3.098') * height) - (Decimal('4.330') * Decimal(str(age)))
    rec_kcal = bmr * Decimal('1.55')  # 보통 활동량

    # 탄, 단, 지 비율 설정 5:3:2
    rec_car = (rec_kcal * Decimal('0.5')) / Decimal('4')  # 1g 4kcal
    rec_prot = (rec_kcal * Decimal('0.3')) / Decimal('4')  # 1g 4kcal
    rec_fat = (rec_kcal * Decimal('0.2')) / Decimal('9')  # 1g 9kcal

    rec_kcal = rec_kcal.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    rec_car = rec_car.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    rec_prot = rec_prot.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    rec_fat = rec_fat.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    return {
        "rec_kcal": rec_kcal,
        "rec_car": rec_car,
        "rec_prot": rec_prot,
        "rec_fat": rec_fat
    }