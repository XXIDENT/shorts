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

## 업로드 시간표 (2026-11-14부터)

| KST | 시리즈 |
|---|---|
| 08:00 | 직업체험 |
| 12:00 | 세계여행 |
| 19:00 | 세계여행 |
| 21:00 | 직업체험 |

GitHub 예약 실행은 몇 시간씩 늦어서 쓰지 않고, Claude 예약 작업이 각 시각 8분 전에 workflow_dispatch로 실행합니다. 같은 시리즈를 4시간 안에 두 번 올리지 않도록 막아 둡니다(`shorts/once.py`). 세계 랭킹·트렌드(`daily.yml`)는 수동 실행 전용이에요.

## 조회수 리포트 (매일 22:30)

`.github/workflows/stats.yml`이 채널 전체 조회수, 어제보다 늘어난 조회수, 최근 90일 조회수(수익화 기준 대비), 시리즈별(올라간 시각 기준) 합계, TOP 5를 모아 **"📊 조회수 리포트" 이슈에 댓글**로 남깁니다. 이슈를 구독하면 알림으로 받아요. 기록은 `data/views.json`(120일치). Actions에서 '조회수 리포트'를 수동 실행하면 바로 볼 수 있습니다.

## 인스타그램 릴스 같이 올리기 (Make.com, 0원)

직업체험·세계여행 영상은 유튜브에 올린 뒤 같은 영상을 인스타 릴스로도 보냅니다. `MAKE_IG_WEBHOOK_URL` 시크릿이 없으면 인스타는 건너뛰어요.

1. 인스타 계정을 **프로페셔널(크리에이터 또는 비즈니스)** 으로 바꾸고 **페이스북 페이지에 연결**합니다(인스타 API 조건).
2. Make.com에서 새 시나리오: **Webhooks > Custom webhook** → **Instagram for Business > Create a Reel Post**
   - Video URL: `video_url`, Caption: `caption`
3. 웹훅 주소를 GitHub Secrets에 `MAKE_IG_WEBHOOK_URL`로 저장하고 시나리오를 켭니다.

인스타 API는 파일 대신 공개 주소의 영상을 가져가서, 영상을 이 저장소의 `reels-media` 릴리스에 임시로 올립니다(최근 40개만 남김). 인스타 전송이 실패해도 유튜브 업로드는 그대로예요.

## 주제 추가
`config/topics.yaml`에 [세계은행 지표 코드](https://data.worldbank.org/indicator)와 제목을 추가하면 됩니다.

## 정책 메모
- 매 영상이 서로 다른 실제 데이터를 다루고, 문장도 여러 변형 중 골라 '반복·대량생산 콘텐츠'로 보이지 않게 했습니다.
- 배경음악은 넣지 않았습니다 (저작권 위험 없음). 넣으려면 YouTube 오디오 라이브러리의 무료 음원을 쓰세요.
- 조회수 구매, 봇, 타인 영상 재업로드는 하지 않습니다.

## 픽셀 직업체험 시리즈 (AI 신입 '모니')

모니터 머리 로봇 '모니'가 직업 하나를 골라 퀘스트 3개를 해 보고, 마지막에 Frey & Osborne(2013, 옥스퍼드대) 연구의 실제 자동화 확률과 모니의 체감 점수를 비교하는 40초대 쇼츠입니다. 그림, 음악, 효과음은 모두 코드로 만들고(외부 이미지 없음), 목소리는 edge-tts입니다.

- 대본: `config/jobs.yaml` (편마다 직접 씀, 같은 문장 재사용 금지는 테스트로 검사)
- 무대: `shorts/pixel/scenes.py`, 그림: `shorts/pixel/art.py`, 음악: `shorts/pixel/chiptune.py`
- 실행: `python -m shorts.jobs --job barista --no-upload`, 정지 화면만: `--frames 1,10,30`
- 워크플로: `.github/workflows/jobs.yml` (매일 21시 KST 1편 자동 업로드, PR에서는 샘플만 만듦)
- 로컬 폰트: `sudo apt install fonts-unifont`

## 모니 세계여행 (픽셀 3D, 매일 19시)

모니가 나라 하나의 거리를 걸으며 세계은행 최신 데이터로 그 나라와 한국을 비교하는 쇼츠입니다. 마인크래프트 같은 복셀(3D 픽셀) 화면을 numpy 레이캐스터로 직접 그려서 별도 3D 프로그램이나 비용이 필요 없습니다. 카메라는 하늘에서 내려와 모니 뒤 3인칭으로 따라가고, 랜드마크는 모니 눈높이 1인칭, 문화 이야기는 셀카 시점으로 바뀝니다.

- 나라와 대사: `config/travel.yaml` (20개국), 세계: `shorts/pixel/world.py`, 렌더러: `shorts/pixel/voxel.py`
- 실행: `python -m shorts.travel --country france --no-upload`, 오프라인: `--offline --tts silent`
- 워크플로: `.github/workflows/travel.yml` (기존 19시 세계 랭킹 자리)
