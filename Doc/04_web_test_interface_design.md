.display = 'none';
            document.getElementById('resultArea').style.display = 'block';
            
            const confidence = result.confidence || 0;
            document.getElementById('confidence').textContent = `${Math.round(confidence * 100)}%`;
            document.getElementById('confidenceBar').style.width = `${confidence * 100}%`;
            
            document.getElementById('customerName').textContent = result.customer_name || '추출 실패';
            document.getElementById('phone').textContent = result.contact_number || '추출 실패';
            document.getElementById('address').textContent = result.delivery_address || '추출 실패';
            
            // 상품 목록
            if (result.items && result.items.length > 0) {
                const itemsHtml = result.items.map(item => 
                    `${item.product_name} x${item.quantity} = ${item.subtotal.toLocaleString()}원`
                ).join('<br>');
                document.getElementById('items').innerHTML = itemsHtml;
            } else {
                document.getElementById('items').textContent = '추출 실패';
            }
            
            document.getElementById('total').textContent = 
                result.expected_amount ? `${result.expected_amount.toLocaleString()}원` : '-';
            
            // JSON 출력
            document.getElementById('jsonOutput').textContent = 
                JSON.stringify(result, null, 2);
        }
        
        function localParse(message) {
            // 간단한 로컬 파싱 (데모용)
            const nameMatch = message.match(/(?:이름|성함)[:\s]*([가-힣]{2,4})/);
            const phoneMatch = message.match(/(010[-\s]?\d{4}[-\s]?\d{4})/);
            const addressMatch = message.match(/(?:주소|배송지)[:\s]*(.+?)(?:\n|$)/);
            
            return {
                customer_name: nameMatch ? nameMatch[1] : null,
                contact_number: phoneMatch ? phoneMatch[1].replace(/\s/g, '-') : null,
                delivery_address: addressMatch ? addressMatch[1].trim() : null,
                items: [],
                expected_amount: 0,
                confidence: 0.75
            };
        }
        
        function addToRecent(sender, message, result) {
            const list = document.getElementById('recentMessages');
            const item = document.createElement('div');
            item.className = 'message-item';
            item.innerHTML = `
                <div class="sender">${sender || '알 수 없음'}</div>
                <div class="preview">${message.substring(0, 50)}...</div>
                <div class="time">${new Date().toLocaleTimeString()}</div>
            `;
            item.onclick = () => {
                document.getElementById('sender').value = sender;
                document.getElementById('message').value = message;
            };
            list.insertBefore(item, list.firstChild);
        }
    </script>
</body>
</html>
```

---

## 5. Option C: Mac iMessage 연동

### 5.1 동작 원리

```
iPhone SMS → iCloud 동기화 → Mac 메시지 앱 → AppleScript → 웹서버
```

### 5.2 요구사항
- Mac 컴퓨터
- iPhone과 동일 Apple ID
- iCloud 메시지 동기화 활성화

### 5.3 AppleScript 구현

```applescript
-- SMSForwarder.scpt
on run
    tell application "Messages"
        set targetChats to every chat whose service type is "SMS"
        
        repeat with targetChat in targetChats
            set msgs to messages of targetChat
            set latestMsg to item 1 of msgs
            
            if (date received of latestMsg) > (lastProcessedDate) then
                set senderPhone to handle of sender of latestMsg
                set msgContent to text of latestMsg
                
                -- 웹서버로 전송
                do shell script "curl -X POST " & ¬
                    "-H 'Content-Type: application/json' " & ¬
                    "-d '{\"sender\": \"" & senderPhone & "\", \"content\": \"" & msgContent & "\"}' " & ¬
                    "https://your-server.com/webhook/sms"
            end if
        end repeat
    end tell
end run
```

### 5.4 자동 실행 설정

```bash
# crontab 설정 (매 분 실행)
* * * * * osascript /path/to/SMSForwarder.scpt
```

---

## 6. 서버 API 구현

### 6.1 Flask 서버

```python
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import json
from datetime import datetime
import sqlite3

app = Flask(__name__)
CORS(app)

# SMS Order Agent 임포트
from sms_order_agent import SMSOrderAgent
agent = SMSOrderAgent()

# 기본 가이드 로드
DEFAULT_GUIDE = """
뷰티하우스에서 공동구매를 시작합니다.
입금계좌: 국민 123-456-789012

[상품 목록]
1번 수분크림 50ml - 32,000원
2번 세럼 30ml - 45,000원
3번 토너 150ml - 25,000원
"""
agent.load_seller_guide(DEFAULT_GUIDE)

# DB 초기화
def init_db():
    conn = sqlite3.connect('messages.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT,
            content TEXT,
            parsed_result TEXT,
            confidence REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/parse/order', methods=['POST'])
def parse_order():
    data = request.json
    message = data.get('message', '')
    sender = data.get('sender', '')
    
    # 에이전트로 파싱
    result = agent.parse_order(message)
    validation = agent.validate_order(result)
    
    # 응답 생성
    response = {
        'customer_name': result.customer_name,
        'contact_number': result.contact_number,
        'delivery_address': result.delivery_address,
        'items': [
            {
                'product_name': item.product_name,
                'quantity': item.quantity,
                'subtotal': item.subtotal
            }
            for item in result.items
        ],
        'expected_amount': result.expected_amount,
        'special_requests': result.special_requests,
        'confidence': result.confidence,
        'validation': validation
    }
    
    # DB 저장
    save_message(sender, message, response)
    
    return jsonify(response)

@app.route('/webhook/sms', methods=['POST'])
def webhook_sms():
    """Shortcuts / Mac에서 호출하는 Webhook"""
    data = request.json
    sender = data.get('sender', '')
    content = data.get('content', '')
    
    # 파싱 처리
    result = agent.parse_order(content)
    
    response = {
        'status': 'success',
        'customer_name': result.customer_name,
        'confidence': result.confidence
    }
    
    return jsonify(response)

@app.route('/api/messages', methods=['GET'])
def get_messages():
    """최근 메시지 목록"""
    conn = sqlite3.connect('messages.db')
    c = conn.cursor()
    c.execute('SELECT * FROM messages ORDER BY created_at DESC LIMIT 20')
    rows = c.fetchall()
    conn.close()
    
    messages = [
        {
            'id': row[0],
            'sender': row[1],
            'content': row[2],
            'parsed_result': json.loads(row[3]) if row[3] else None,
            'confidence': row[4],
            'created_at': row[5]
        }
        for row in rows
    ]
    
    return jsonify(messages)

def save_message(sender, content, parsed):
    conn = sqlite3.connect('messages.db')
    c = conn.cursor()
    c.execute(
        'INSERT INTO messages (sender, content, parsed_result, confidence) VALUES (?, ?, ?, ?)',
        (sender, content, json.dumps(parsed), parsed.get('confidence', 0))
    )
    conn.commit()
    conn.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
```

---

## 7. 배포 가이드

### 7.1 로컬 테스트

```bash
# 1. 가상환경 생성
python -m venv venv
source venv/bin/activate  # Mac/Linux
# venv\Scripts\activate    # Windows

# 2. 의존성 설치
pip install flask flask-cors

# 3. 서버 실행
python server.py

# 4. 브라우저에서 접속
open http://localhost:8000
```

### 7.2 클라우드 배포 (ngrok)

```bash
# ngrok 설치 및 실행
ngrok http 8000

# 생성된 URL을 Shortcuts에서 사용
# https://xxxx-xxx-xxx.ngrok.io/webhook/sms
```

### 7.3 프로덕션 배포

```yaml
# docker-compose.yml
version: '3.8'
services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - FLASK_ENV=production
    volumes:
      - ./data:/app/data
```

---

## 8. 사용 시나리오

### 8.1 기본 테스트 흐름

```
1. iPhone에서 SMS 수신
2. 메시지 내용 복사 (길게 누르기 → 복사)
3. Safari에서 웹 인터페이스 접속
4. 메시지 붙여넣기
5. "주문 파싱" 클릭
6. 결과 확인
```

### 8.2 Shortcuts 자동화 흐름

```
1. iPhone에서 SMS 수신
2. 메시지 선택 후 공유 → "SMS to Agent"
3. 자동으로 서버 전송
4. 웹 대시보드에서 결과 확인
```

---

## 9. 향후 개선 계획

| 단계 | 내용 | 예상 기간 |
|------|------|----------|
| v1.1 | PWA 지원 (홈 화면 추가) | 1주 |
| v1.2 | 실시간 알림 (WebSocket) | 2주 |
| v2.0 | 판매자 가이드 관리 UI | 2주 |
| v2.1 | 다중 판매자 지원 | 2주 |
| v3.0 | Android 전용 앱 | 4주 |

---

**작성일**: 2025-12-22  
**버전**: 1.0.0
