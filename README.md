# 불법광고 탐지 백엔드 - SQLite 버전

이 프로젝트는 SQLite를 사용합니다. MySQL 서버 설치나 비밀번호 설정은 필요하지 않습니다. Python에 포함된 `sqlite3` 모듈을 사용합니다.

## 폴더 구성

- `database/db.py`: SQLite 연결 및 DB 파일 위치 설정
- `database/models.py`: `analysis`, `findings` 테이블 생성
- `database/repository.py`: 분석 결과 저장 및 조회
- `detector/detector.py`: 광고 탐지, `result.json` 저장, SQLite 저장 연동
- `detector/test_detector.py`: 탐지 테스트

## 실행 방법 (VS Code / Windows)

1. ZIP 파일을 압축 해제합니다.
2. VS Code에서 압축을 푼 `Backend-feat-database-sqlite` 폴더를 엽니다.
3. 메뉴 `터미널 > 새 터미널`을 누릅니다.
4. 터미널 경로가 프로젝트 최상위 폴더인지 확인합니다. `database`와 `detector` 폴더가 보여야 합니다.
5. SQLite 연결을 확인합니다.

```bash
python -m database.db
```

6. 테이블을 생성합니다.

```bash
python -m database.models
```

7. 탐지 및 DB 저장 연동을 테스트합니다.

```bash
python -m detector.test_detector
```

테스트 중 `detector/result.json` 파일과 `database/results.db` SQLite DB 파일이 생성될 수 있습니다. `run_detection()`이 실행되면 검사 메타정보는 `analysis`에, 개별 탐지 결과는 `findings`에 저장됩니다.

## DB 저장/조회 함수

`database.repository`에서 아래 함수를 제공합니다.

- `save_scan_result(result)`: `result`의 `meta`와 `findings`를 DB에 저장하고 검사 ID를 반환합니다.
- `get_scan_result(analysis_id)`: 특정 검사와 그 탐지 결과를 조회합니다.
- `get_scan_history()`: 전체 검사 이력을 조회합니다.

예시 (프로젝트 최상위 폴더에서 실행):

```python
from database.models import create_tables
from database.repository import get_scan_history, get_scan_result

create_tables()
print(get_scan_history())
print(get_scan_result(1))
```

## 주의사항

- SQLite DB는 `database/results.db` 파일로 저장됩니다. 별도 DB 서버가 필요 없습니다.
- 팀에서 기존 백엔드 실행 방식이 따로 있다면, 먼저 팀원과 상의하고 이 변경 사항을 통합하세요.
- `test_detector.py`는 테스트 데이터로 탐지 코드를 실행하는 파일입니다. 실제 웹사이트 크롤링 기능 자체를 대신하지는 않습니다.
