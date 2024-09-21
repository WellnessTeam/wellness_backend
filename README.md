# Wellness(backend)

## directory structure

### app/
1. ```app/v1/```
- API 버전 관리

2. ```core/```
- config.py: 설정 파일
- logging.py: 로깅 관련 설정 및 기능 관리
- security.py: 보안관련 기능을 정의, 인증, 권한 설정 등

3. ```db/```: 데이터베이스 관련 코드들이 포함된 디렉토리
- crud.py: Create, Read, Update, Delete 관련 데이터베이스 작업을 처리
- models.py: 데이터베이스 테이블 스키마를 정의한 모델 파일
- session.py: DB 세션 관리를 위한 코드

4. ```schemas/```
- FastAPI에서 사용하는 Pydantic 모델들, 즉 스키마 정의 파일

5. ```services/```: 비즈니스 로직을 담당하는 디렉토리로, 각 서비스에 필요한 로직이 파일별로 분리되어 있음
- auth.service.py: 인증 관련 서비스 로직
- recommend_serivce.py: 추천 관련 서비스 로직

6. ```utils/```:
- 애플리케이션 코드들이 들어가는 곳으로, 애플리케이션 전반에서 공통적으로 사용함
..