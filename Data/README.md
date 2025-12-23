# 📊 Data Module

프로젝트의 성능 평가를 위한 데이터셋과 에이전트 실행 결과, 시각화 리포트를 관리하는 폴더입니다.

## 📂 폴더 구조
- **test_data/**: Agent 검증에 사용되는 데이터입니다.
  - `test_image/`: 송금 내역 생성 이미지입니다.
  - `transfer_images_labels_accurate.json`: OCR 및 데이터 추출 성능 측정을 위한 정답지(Ground Truth) 파일입니다.
- **test_result/**: 에이전트 테스트 시 생성된 실행 로그와 성능 지표(CSV)가 저장됩니다.
- **transfer_image/**: 입금 확인 테스트를 위해 임시로 저장되는 이체 확인증 이미지 보관소입니다.
- **visualize_data/**: 테스트 결과를 분석한 시각화 자료입니다.
  - Heatmap: 항목별 추출 정확도 분석
  - Item/Turn Plot: 주문 완료까지 걸리는 대화 턴 수 및 성능 분포

## 📈 MLOps 활용
본 폴더의 데이터는 에이전트의 프롬프트 수정이나 모델 변경 시, **정확도(Accuracy)**와 **누락률**을 정량적으로 비교하는 벤치마크 자료로 활용됩니다.