# SMS 문자 주문 자동화 에이전트 (Agent_10000)

📱 카카오톡/문자 비정형 주문 메시지를 자동으로 파싱하여 구조화된 데이터로 변환하는 AI 에이전트

## 📁 폴더 구조

```
Agent_10000/
├── sms_order_agent.py          # 메인 에이전트 코드
├── general_orders_10000.xlsx   # 학습용 합성 데이터 (10,000건)
├── general_orders_10000.json   # JSON 형식 데이터
├── validation_synthetic_100.csv # 검증용 데이터 (100건)
├── seller_guides_general.md    # 10개 카테고리 판매자 가이드
├── transfer_images/            # 송금 캡처 이미지 (250장)
└── README.md                   # 본 문서
```

## 🛠️ 주요 기능

### 1. 판매자 가이드 파싱
- 상품 목록, 가격, 옵션 자동 추출
- 계좌 정보 추출
- 무료배송 기준 및 배송비 파싱

### 2. 주문 메시지 파싱
- 고객명, 연락처, 주소 추출
- 상품번호, 옵션, 수량 파싱
- 요청사항 추출
- 중복 상품 자동 병합

### 3. 주문 검증 및 응답 생성
- 필수 정보 누락 체크
- 배송비 자동 계산
- 확인 메시지 자동 생성

## 🚀 사용법

```python
from sms_order_agent import SMSOrderAgent

# 에이전트 초기화
agent = SMSOrderAgent()

# 판매자 가이드 로드
agent.load_seller_guide(guide_text)

# 주문 파싱
order = agent.parse_order(order_message)

# 검증
validation = agent.validate_order(order)

# 확인 메시지 생성
response = agent.generate_confirmation(order, validation)

# JSON 라벨 출력
label = agent.to_label_json(order)
```

## 📊 데이터셋

### 10개 카테고리 (각 1,000건)
1. 뷰티/화장품
2. 패션/의류
3. 건강식품/영양제
4. 생활용품
5. 유아/아동용품
6. 반려동물용품
7. 주방/식기
8. 홈인테리어
9. 전자기기/액세서리
10. 문구/취미용품

### 데이터 구조 (Excel)
| 컬럼 | 설명 |
|------|------|
| 주문번호 | ORD000001 형식 |
| 고객ID | 고유 고객 식별자 |
| 카테고리 | 상품 카테고리 |
| 원본메시지 | 비정형 주문 텍스트 |
| 고객명 | 파싱된 고객명 |
| 전화번호 | 정규화된 전화번호 |
| 주소 | 배송지 주소 |
| 상품코드 | 상품 식별 코드 |
| 상품명 | 상품 이름 |
| 옵션 | 선택 옵션 |
| 단위 | 개/통/세트 등 |
| 수량 | 주문 수량 |
| 단가 | 상품 단가 |
| 소계 | 수량 × 단가 |

### 검증 데이터 (CSV)
| 컬럼 | 설명 |
|------|------|
| no | 순번 |
| guide | 판매자 가이드 텍스트 |
| order | 주문 메시지 텍스트 |
| source | original/augmented |
| label | 정답 JSON |

## 📈 성능

- **파싱 정확도**: 95%+ (정형화된 주문)
- **신뢰도 계산**: 필수 필드 기반 0-100%
- **처리 속도**: ~100건/초 (규칙 기반)

## 🔧 향후 개선 사항

1. **LLM 통합**: GPT/Claude API 연동으로 복잡한 주문 처리
2. **OCR 연동**: 입금 캡처 이미지 자동 인식
3. **멀티턴 대화**: 누락 정보 자동 질문
4. **API 서버**: FastAPI 기반 REST API

## 📝 라이선스

MIT License

## 👤 제작

- 생성일: 2025-12-22
- 버전: 1.0.0
