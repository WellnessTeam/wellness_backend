import logging
from fastapi import APIRouter, HTTPException, Request, Depends
import requests
from dotenv import load_dotenv
import os

router = APIRouter()

# 환경 변수 로드
load_dotenv()

# 카카오 API 키와 리다이렉트 URL을 환경 변수에서 가져오기
kakao_restapi_key = os.getenv("KAKAO_RESTAPI_KEY")
kakao_redirect_url = os.getenv("KAKAO_REDIRECT_URL")

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@router.post("/code/kakao")
async def get_kakao_token(request: Request):
    try:
        # 요청에서 JSON 데이터를 받아오기
        data = await request.json()   
        authorization_code = data.get("code").strip()   # 공백제거

        if not authorization_code:
            # 인가 코드가 없을 경우 로그 남기기
            logger.error("요청에 인가 코드가 없습니다.")
            raise HTTPException(status_code=400, detail="Authorization code is missing")

        # 인가 코드 로그로 기록
        logger.info(f"인가 코드 수신: {authorization_code}")

        # 환경 변수 로그로 기록 (제대로 로드되었는지 확인)
        logger.info(f"Kakao REST API Key: {kakao_restapi_key}")
        logger.info(f"Kakao Redirect URL: {kakao_redirect_url}")

        # 카카오 토큰 요청 URL 및 파라미터 설정
        token_url = "https://kauth.kakao.com/oauth/token"
        params = {
            "grant_type": "authorization_code",
            "client_id": kakao_restapi_key,
            "redirect_uri": kakao_redirect_url,
            "code": authorization_code
        }

        # 카카오 API로 요청 보내기 전에 요청 내용 로그 기록
        logger.info(f"{token_url}로 POST 요청을 보냅니다. 파라미터: {params}")

        # 카카오 API에 POST 요청 보내기
        response = requests.post(token_url, data=params)

        # 응답 상태 코드와 응답 내용 로그로 기록
        logger.info(f"응답 상태 코드: {response.status_code}")
        logger.info(f"응답 내용: {response.text}")

        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data.get("access_token")
            if not access_token:
                logger.error("엑세스 토큰을 가져오는 데 실패했습니다.")
                raise HTTPException(status_code=500, detail="Failed to retrieve access token")
            
            return {"access_token": access_token}
        
        else:
            error_details = response.json()
            error_code = error_details.get("error")
            error_description = error_details.get("error_description")
            logger.error(f"엑세스 토큰을 가져오는 데 실패했습니다. 오류: {error_code}, 설명: {error_description}")
            raise HTTPException(status_code=response.status_code, detail=f"{error_description} (Error Code: {error_code})")


    except requests.exceptions.RequestException as e:
        logger.error(f"네트워크 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Network error: {str(e)}")
    except Exception as e:
        logger.error(f"예상치 못한 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")