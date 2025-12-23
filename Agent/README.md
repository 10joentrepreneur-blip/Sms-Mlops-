# 🤖 Agent Module

문자 주문 자동화 시스템의 핵심 로직과 실행을 담당하는 모듈입니다. Google Vertex AI(Gemini)를 기반으로 비정형 텍스트를 분석하고 주문 데이터를 생성합니다.

## 📂 주요 파일 구성
- **agent_engine.py**: `TextOrderAgent` 클래스가 정의된 핵심 엔진입니다. Vertex AI와 도구 호출(Tool Calling)을 관리합니다.
- **run.py**: 시스템 실행 엔트리 포인트입니다. 환경 설정에 따라 'Local CLI' 또는 'FastAPI Server' 모드로 구동됩니다.
- **ocr_manager.py**: 입금 확인증 이미지를 분석하여 텍스트 데이터를 추출합니다.
- **price_verifier.py**: 상점 가이드를 참조하여 주문 항목의 가격과 총합계를 검증합니다.
- **api.py & cli.py**: 각각 서버 인터페이스와 로컬 테스트용 인터페이스를 제공합니다.

## 🛠 주요 기능
1. **자연어 주문 처리**: 고객의 일상적인 문장에서 상품명, 수량, 주소, 연락처 등을 자동으로 추출합니다.
2. **도구 호출(Tool Calling)**: `update_order_state`, `get_store_info`, `verify_payment` 등 내부 기능을 LLM이 직접 실행합니다.
3. **주소 및 가격 검증**: `guides/` 폴더의 지식 베이스를 참조하여 주소의 완전성과 결제 금액의 정확도를 체크합니다.
4. **결제 확인 자동화**: 사용자가 보낸 이체 캡처 이미지를 OCR로 읽어 실제 주문 내역과 대조합니다.

## 🚀 실행 방법
```bash
# 로컬 CLI 모드 실행
python run.py (EXECUTION_MODE=local)

# 서버 모드 실행
python run.py (EXECUTION_MODE=server)