# 개인 일정 관리 에이전트 (Personal Calendar Agent)

자연어 처리 기능을 갖춘 개인 일정 관리 에이전트입니다. 이 애플리케이션은 사용자의 일정과 작업을 관리하고, 자연어 명령어를 통해 조작할 수 있는 API를 제공합니다.

## 기능

- 💬 **자연어 명령어 처리**: "내일 오후 2시에 회의 일정 추가해줘" 같은 자연어 명령을 처리
- 📅 **일정 관리**: 일정 생성, 조회, 수정, 삭제
- ✅ **작업 관리**: 작업 생성, 조회, 수정, 삭제, 상태 변경
- 🔔 **알림 기능**: 일정 및 작업에 대한 알림 제공
- 🔐 **사용자 인증**: JWT 기반 사용자 인증
- 📱 **RESTful API**: 모바일/웹 애플리케이션 연동 가능한 API 제공

## 기술 스택

- **Backend**: [FastAPI](https://fastapi.tiangolo.com/)
- **데이터베이스**: SQLite (개발), PostgreSQL (프로덕션)
- **ORM**: SQLAlchemy
- **자연어 처리**: spaCy, NLTK
- **인증**: JWT(JSON Web Tokens)
- **컨테이너화**: Docker, Docker Compose
- **테스트**: pytest

## 시작하기

### 요구사항

- Python 3.9 이상
- pip
- Docker 및 Docker Compose (선택적)

### 설치 방법

#### 로컬 개발 환경

1. 저장소 복제:

    ```bash
    git clone https://github.com/BearMett/personal-calendar.git
    cd personal-calendar
    ```

2. 가상환경 생성 및 활성화:

    ```bash
    python -m venv venv
    source venv/bin/activate  # Windows: venv\Scripts\activate
    ```

3. 의존성 설치:

    ```bash
    pip install -r requirements.txt
    ```

4. spaCy 모델 다운로드:

    ```bash
    python -m spacy download en_core_web_sm
    ```

5. 환경 변수 설정:

    ```bash
    cp .env.example .env
    # .env 파일을 편집하여 환경 변수 설정
    ```

6. 애플리케이션 실행:

    ```bash
    cd personal-calendar
    python run.py
    ```

7. 브라우저에서 `http://localhost:8000/api/docs`에 접속하여 API 문서 확인

#### Docker를 사용한 설치

1. Docker Compose로 애플리케이션 실행:

    ```bash
    docker-compose up -d
    ```

2. 브라우저에서 `http://localhost:8000/api/docs`에 접속하여 API 문서 확인

## API 엔드포인트

API는 다음과 같은 주요 엔드포인트를 제공합니다:

### 인증

- `POST /api/auth/register`: 새 사용자 등록
- `POST /api/auth/login`: 로그인 및 토큰 발급
- `GET /api/auth/me`: 현재 사용자 정보 조회

### 일정

- `GET /api/events`: 일정 목록 조회
- `POST /api/events`: 새 일정 생성
- `POST /api/events/parse`: 자연어로 일정 생성
- `GET /api/events/{event_id}`: 특정 일정 조회
- `PUT /api/events/{event_id}`: 일정 수정
- `DELETE /api/events/{event_id}`: 일정 삭제

### 작업

- `GET /api/tasks`: 작업 목록 조회
- `POST /api/tasks`: 새 작업 생성
- `POST /api/tasks/parse`: 자연어로 작업 생성
- `GET /api/tasks/{task_id}`: 특정 작업 조회
- `PUT /api/tasks/{task_id}`: 작업 수정
- `DELETE /api/tasks/{task_id}`: 작업 삭제
- `PUT /api/tasks/{task_id}/status`: 작업 상태 변경

### 에이전트

- `POST /api/agent/command`: 자연어 명령어 처리

## 자연어 명령어 예시

에이전트는 다음과 같은 자연어 명령어를 처리할 수 있습니다:

- "내일 오후 2시에 존과 회의 일정 추가해줘"
- "다음 주 월요일 10시에 팀 미팅 일정 추가해줘"
- "금요일까지 보고서 제출 작업 추가해줘"
- "이번 주 일정 보여줘"
- "완료된 작업 목록 보여줘"
- "작업 #5 완료로 표시해줘"

## 테스트

단위 테스트와 통합 테스트를 실행하려면:

```bash
# 단위 테스트 실행
pytest app/utils/auth.test.py
pytest app/services/nlp.test.py

# 통합 테스트 실행
pytest tests/
```

## 배포

이 애플리케이션은 Docker와 Docker Compose를 사용하여 간단하게 배포할 수 있습니다:

1. 프로덕션 환경 변수 설정:

    ```bash
    cp .env.example .env
    # .env 파일을 편집하여 프로덕션 환경에 맞게 설정
    ```

2. Docker Compose로 애플리케이션 실행:

    ```bash
    docker-compose up -d
    ```

## 구조

```bash
personal-calendar/
├── app/                  # 애플리케이션 코드
│   ├── models/           # SQLAlchemy 모델
│   ├── routes/           # API 라우트
│   ├── schemas/          # Pydantic 스키마
│   ├── services/         # 비즈니스 로직
│   ├── utils/            # 유틸리티 함수
│   ├── templates/        # HTML 템플릿
│   └── static/           # 정적 파일
├── tests/                # 통합 테스트
├── config.py             # 애플리케이션 설정
├── run.py                # 애플리케이션 진입점
├── requirements.txt      # 의존성 목록
├── .env.example          # 환경 변수 예제
├── Dockerfile            # Docker 이미지 구성
└── docker-compose.yml    # Docker Compose 구성
```

## 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.
