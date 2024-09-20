# /app/utils/image_processing.py
from PIL import Image, ExifTags, UnidentifiedImageError
from io import BytesIO
import datetime
from fastapi import HTTPException, status

def extract_exif_data(file_bytes: bytes):
    try:
        img = Image.open(BytesIO(file_bytes))
        exif_data = img._getexif()
        
        if not exif_data:
            return None
        
        for tag, value in exif_data.items():
            decoded_tag = ExifTags.TAGS.get(tag, tag)
            if decoded_tag == "DateTimeOriginal":
                return value  # 예: '2022:03:15 10:20:35'
        return None 
    
    except UnidentifiedImageError:
        return HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail={
                "status": "ForBidden",
                "status_code": "403",
                "detail": "invalid image format."
            }
        )
    
    except AttributeError:
        return HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "status": "ForBidden",
                "status_code": "403",
                "detail": f"Error: {str(e)}"
            }
        )

def determine_meal_type(taken_time: str) -> str:
    try:
        time_format = "%Y:%m:%d %H:%M:%S"
        
        # Exif 데이터가 없으면 현재 시간을 사용
        if isinstance(taken_time, str):
            taken_time_obj = datetime.datetime.strptime(taken_time, time_format)  # 문자열을 datetime 객체로 변환
        else:
            taken_time_obj = datetime.datetime.now()  # Exif 데이터가 없을 경우 현재 서버 시간을 사용
        
        # datetime 모듈을 명확하게 호출
        taken_time_obj = datetime.datetime.strptime(taken_time, time_format)  # datetime의 datetime 모듈 사용
        hour = taken_time_obj.hour
        if 6 <= hour <= 8:
            return "아침"
        elif 11 <= hour <= 13:
            return "점심"
        elif 17 <= hour <= 19:
            return "저녁"
        else:
            return "기타"
        
    except ValueError as e:
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "status": "Bad Request",
                "status_code": "400",
                "detail": f"Invalid datetime format: {str(e)}"
            }
        )
    except Exception as e:
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "status": "Bad Request",
                "status_code": "400",
                "detail": f"Error: {str(e)}"
            }
        )