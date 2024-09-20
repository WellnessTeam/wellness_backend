from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, status
import requests
from sqlalchemy.orm import Session
from api.v1.auth import validate_token
from db.session import get_db
from db.crud import get_food_by_category, get_recommend_by_user
from utils.image_processing import extract_exif_data, determine_meal_type
from utils.s3 import upload_image_to_s3
import mimetypes  # mimetypes 모듈 추가
from io import BytesIO
import os
import uuid
import datetime
from fastapi.responses import JSONResponse
from decimal import Decimal
from db import models

router = APIRouter()

# 허용된 이미지 파일 형식 (MIME 타입)
ALLOWED_MIME_TYPES = ["image/jpeg", "image/png", "image/jpg"]

# Decimal 타입을 float으로 변환하는 함수
def decimal_to_float(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

@router.post("/predict")
async def classify_image(
    current_user: models.User = Depends(validate_token),  # 토큰 검증 추가
    file: UploadFile = File(...), 
    db: Session = Depends(get_db)
):
    try:
        file_bytes = await file.read()
        file_extension = file.filename.split(".")[-1]
        unique_file_name = f"{uuid.uuid4()}.{file_extension}"
        bucket_name = os.getenv("BUCKET_NAME", "default_bucket_name")
        
        # MIME 타입 확인을 위해 파일 확장자를 기반으로 MIME 타입을 추론
        mime_type, _ = mimetypes.guess_type(file.filename)

        # 허용된 MIME 타입 목록에 없는 경우 에러 반환
        if mime_type not in ALLOWED_MIME_TYPES:
            return JSONResponse(
                {
                    "status": "ForBidden",
                    "status_code": 403,
                    "detail": "Invalid file type. Allowed types: jpg, jpeg, png."
                },
                status_code=status.HTTP_403_FORBIDDEN
            )
        # 이미지 S3 업로드 처리
        try:
            image_url = upload_image_to_s3(BytesIO(file_bytes), bucket_name, unique_file_name)
        except Exception as e:
            return JSONResponse(
                {
                    "status": "Bad Request",
                    "status_code": 403,
                    "detail": f"failed to upload image to s3: {str(e)}"
                },
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        # EXIF 데이터에서 날짜 추출
        date = extract_exif_data(file_bytes)
        if date is None:
            date = datetime.datetime.now().strftime("%Y:%m:%d %H:%M:%S")  # 현재 시간을 문자열로 설정
        
        # meal_type 및 meal_type_id 설정
        meal_type = determine_meal_type(date) if date else "기타"
        
        # 식사 종류에 따른 ID를 수동으로 설정 (예시: 아침 -> 1, 점심 -> 2, 저녁 -> 3, 기타 -> 4)
        meal_type_id_map = {
            "아침": 0,
            "점심": 1,
            "저녁": 2,
            "기타": 3
        }
        
        meal_type_id = meal_type_id_map.get(meal_type, 3)  # 기본값을 기타로 설정

        # Model API 호출
        model_api_url = "http://127.0.0.1:8001/predict_url/"
        try:
            response = requests.post(model_api_url, params={"image_url": image_url})
            response.raise_for_status()
        except requests.RequestException as e:
            return JSONResponse(
                {
                    "status": "Internal Server Error",
                    "status_code": 500,
                    "detail": f"Model API request failed: {str(e)}"
                },
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # 모델 응답에서 category_id 가져오기
        category_id = response.json().get("category_id")
        if category_id is None:
            return JSONResponse(
                {
                    "status": "Bad Request",
                    "status_code": 400,
                    "detail": "Category ID is required"
                },
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # 음식 카테고리 가져오기
        food = get_food_by_category(db, category_id)
        if not food:
            return JSONResponse(
                {
                    "status": "Not Found",
                    "status_code": 404,
                    "detail": "Food category not found"
                },
                status_code=status.HTTP_404_NOT_FOUND
            )

        # 사용자 권장 영양소 정보 가져오기
        recommend = get_recommend_by_user(db, current_user)
        if not recommend:
            return JSONResponse(
                {
                    "status": "Not Found",
                    "status_code": 404,
                    "detail": "Recommendation not found"
                },
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # meal_type과 category_name을 UTF-8로 인코딩
        meal_type_utf8 = meal_type.encode('utf-8').decode('utf-8')
        category_name_utf8 = food.category_name.encode('utf-8').decode('utf-8')

        # 응답 반환
        return JSONResponse(
            {
                "status": "success",
                "status_code": 201,
                "detail": {
                    "wellness_image_info": {
                        "date": date,
                        "meal_type": meal_type_utf8,
                        "meal_type_id": meal_type_id,
                        "category_id": category_id,
                        "category_name": category_name_utf8,
                        "food_kcal": decimal_to_float(food.food_kcal),
                        "food_car": round(float(food.food_car)),
                        "food_prot": round(float(food.food_prot)),
                        "food_fat": round(float(food.food_fat)),
                        "rec_kcal": decimal_to_float(recommend.rec_kcal),
                        "rec_car": round(float(recommend.rec_car)),
                        "rec_prot": round(float(recommend.rec_prot)),
                        "rec_fat": round(float(recommend.rec_fat)),
                        "image_url": image_url
                    }
                },
                "message": "Image Classify Information saved successfully"
            },
            media_type="application/json; charset=utf-8"
        )

    except Exception as e:
        return JSONResponse(
            {
                "status": "Internal Server Error",
                "status_code": 500,
                "detail": f"Internal server error: {str(e)}"
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
