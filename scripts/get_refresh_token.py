"""내 컴퓨터에서 한 번만 실행해 YouTube 업로드용 refresh token을 받는다.

1. Google Cloud 콘솔 → API 및 서비스 → 사용자 인증 정보 → OAuth 클라이언트 ID 만들기
   (애플리케이션 유형: 데스크톱 앱) → JSON 다운로드 → 이 폴더에 client_secret.json으로 저장
2. pip install google-auth-oauthlib
3. python scripts/get_refresh_token.py
4. 브라우저에서 유튜브 채널 계정으로 로그인·허용
5. 출력된 세 값을 GitHub 저장소 Settings → Secrets and variables → Actions에 저장
   (이 값들은 채팅이나 코드에 절대 붙여넣지 마세요)
"""
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

# 업로드·수정·삭제 등 채널 관리 전체 권한 + 시청 유지율 같은 분석 숫자 읽기
SCOPES = ["https://www.googleapis.com/auth/youtube", "https://www.googleapis.com/auth/yt-analytics.readonly"]
secret = Path(__file__).resolve().parent / "client_secret.json"
flow = InstalledAppFlow.from_client_secrets_file(str(secret), SCOPES)
creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")
print("\nGitHub Secrets에 아래 값을 저장하세요:\n")
print("YT_CLIENT_ID     =", creds.client_id)
print("YT_CLIENT_SECRET =", creds.client_secret)
print("YT_REFRESH_TOKEN =", creds.refresh_token)
