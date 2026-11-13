# shorts: 세계 순위 데이터 쇼츠 자동 생성기

세계은행 오픈데이터로 "○○가 가장 많은 나라 TOP 10 (한국은 몇 위?)" 세로 영상을 매일 자동으로 만들고 유튜브에 올립니다. 비용은 0원입니다.

## 동작 방식

1. `config/topics.yaml`에서 가장 오래전에 만든 주제를 고름
2. 세계은행 API(키 불필요)에서 최신 데이터를 받아 국가 순위 계산
3. 매번 다른 문장 변형으로 내레이션 대본 생성 (10위→1위 공개, 한국 순위, 마무리 질문)
4. 음성 생성: Google Cloud TTS 무료 한도 → 실패 시 edge-tts → 실패 시 무음
5. Pillow + FFmpeg로 1080x1920 영상 렌더링 (막대 애니메이션, 자막, 출처 표시)
6. YouTube에 **비공개**로 업로드 → YouTube Studio에서 확인 후 공개 (= 사람 검수 단계)
7. `data/history.json`에 기록

GitHub Actions가 매일 한국 시간 08시(세계 랭킹), 12시(실시간 트렌드: 구글 급상승 검색어 / 유튜브 인기 급상승), 19시(세계 랭킹)에 실행합니다. Actions 탭에서 "Run workflow"로 바로 실행할 수도 있어요.

## 처음 설정 (한 번만)

### 1. Google Cloud
1. [Google Cloud 콘솔](https://console.cloud.google.com)에서 프로젝트 생성, 결제 계정 연결 (무료 한도 안에서 사용)
2. **YouTube Data API v3**, **Cloud Text-to-Speech API** 사용 설정
3. API 및 서비스 → 사용자 인증 정보 → **API 키** 만들기 → 키 제한에서 Cloud Text-to-Speech API만 허용
4. OAuth 동의 화면 설정 (외부, 앱 이름 아무거나) → **게시 상태를 '프로덕션'으로 변경**
   - '테스트' 상태로 두면 refresh token이 7일 뒤 만료돼 업로드가 멈춥니다.
5. 사용자 인증 정보 → **OAuth 클라이언트 ID** (데스크톱 앱) 만들기 → JSON 다운로드

### 2. Refresh token 받기 (내 컴퓨터에서)
```bash
pip install google-auth-oauthlib
# 다운로드한 JSON을 scripts/client_secret.json으로 저장
python scripts/get_refresh_token.py
```
브라우저에서 **유튜브 채널을 가진 계정**으로 로그인하고 허용하세요. "확인되지 않은 앱" 경고가 나오면 고급 → 이동을 누르면 됩니다(내 앱이라 안전).

### 3. GitHub Secrets 저장
저장소 Settings → Secrets and variables → Actions → New repository secret

| 이름 | 값 |
|---|---|
| `GOOGLE_TTS_API_KEY` | 1-3에서 만든 API 키 |
| `YT_CLIENT_ID` | 2에서 출력된 값 |
| `YT_CLIENT_SECRET` | 2에서 출력된 값 |
| `YT_REFRESH_TOKEN` | 2에서 출력된 값 |

Secrets가 없으면 영상만 만들고 업로드는 건너뜁니다. 만든 영상은 Actions 실행 화면 맨 아래 Artifacts에서 받을 수 있어요.

### 4. API 감사 신청
API로 올린 영상은 Google 감사를 통과하기 전까지 비공개로만 올라갑니다. [YouTube API 감사 신청서](https://support.google.com/youtube/contact/yt_api_form)를 제출하세요. 통과 후 저장소 Variables에 `YT_PRIVACY=public`을 넣으면 바로 공개로 올라갑니다. 그 전까지는 Studio에서 확인 후 직접 공개하세요.

## 로컬 실행
```bash
sudo apt install fonts-noto-cjk ffmpeg
pip install -r requirements.txt
python -m shorts.main --no-upload                       # 실제 데이터로 생성
python -m shorts.main --topic gdp --no-upload           # 주제 지정
python -m shorts.main --fixtures tests/fixtures --topic population --tts silent --no-upload   # 오프라인
python -m pytest -q
```

## 공개 업로드: Make.com 경유 (감사 통과 전까지)
Google 감사를 받기 전에는 API로 올린 영상이 "비공개 잠김"이 되어 공개할 수 없어요.
그래서 Google 검증을 받은 Make.com을 거쳐 올립니다. 무료 플랜(월 1,000 크레딧)으로 충분해요(영상 1개당 2 크레딧).

1. [make.com](https://www.make.com) 가입 → **Create a new scenario**
2. 첫 모듈: **Webhooks → Custom webhook** → Add → 이름 `shorts` → Save → 나온 **주소 복사**
3. GitHub 저장소 Secrets에 `MAKE_WEBHOOK_URL` = 복사한 주소 저장
4. Actions → **매일 쇼츠 생성** → Run workflow → `no_upload`는 false로 한 번 실행
   (Make가 데이터 구조를 배우도록 첫 전송이 필요해요. 이 첫 영상은 업로드되지 않아요)
5. Make로 돌아가 **+** → **YouTube → Upload a Video** 추가 → 유튜브 계정 연결
   - File: 웹훅의 `video` (파일 이름·데이터)
   - Title: `title`, Description: `description`, Tags: `tags`
   - Privacy status: `privacy` (public)
   - Category: Education, Made for kids: No
6. 오른쪽 아래 스위치를 켜서 시나리오를 **ON**, 스케줄은 **Immediately**

감사 신청 방법은 [docs/api-audit.md](docs/api-audit.md)를 보세요.

## 채널 관리 (삭제·공개·제목 수정)
Actions 탭 → **채널 관리** → Run workflow
- `list`: 채널 영상 목록과 ID 보기
- `delete` + `영상ID`: 영상 삭제
- `privacy` + `영상ID public`: 공개로 전환
- `title` + `영상ID 새 제목`: 제목 수정

## 주제 추가
`config/topics.yaml`에 [세계은행 지표 코드](https://data.worldbank.org/indicator)와 제목을 추가하면 됩니다.

## 정책 메모
- 매 영상이 서로 다른 실제 데이터를 다루고, 문장도 여러 변형 중 골라 '반복·대량생산 콘텐츠'로 보이지 않게 했습니다.
- 배경음악은 넣지 않았습니다 (저작권 위험 없음). 넣으려면 YouTube 오디오 라이브러리의 무료 음원을 쓰세요.
- 조회수 구매, 봇, 타인 영상 재업로드는 하지 않습니다.
