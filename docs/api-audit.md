# YouTube API 감사 신청서 작성 도우미

신청서: https://support.google.com/youtube/contact/yt_api_form
("YouTube API Services - Audit and Quota Extension Form" 선택)

감사를 통과하면 우리 앱으로 올린 영상도 바로 공개할 수 있어요. 그때는 GitHub Secrets에서
`MAKE_WEBHOOK_URL`을 지우면 자동으로 직접 업로드로 돌아가요.

아래 답은 영어로 그대로 붙여넣으면 됩니다. `<>` 부분만 본인 정보로 바꾸세요.

| 항목 | 답변 |
|---|---|
| Organization / Company name | `<본인 이름>` (individual creator) |
| Organization website | https://github.com/XXIDENT/shorts |
| Google Cloud project number | 1028621889645 |
| API client name | shorts |
| Which API services | YouTube Data API v3 |
| Is the API client used by others? | No. Internal tool used only by the channel owner for their own channel. |
| How many users | 1 |

**Describe your API client / use case**

> This is a personal automation tool for my own YouTube channel. Every day it creates up to
> three original data-visualization Shorts (country rankings from World Bank open data, and
> daily trending-topic rankings for Korea), renders them with our own code, and uploads them to
> my channel with videos.insert. I also use videos.update / videos.delete to fix titles or
> remove videos, and videos.list (chart=mostPopular, regionCode=KR) to read public trending data.
> No third-party user data is collected or stored. OAuth tokens are kept in encrypted GitHub
> repository secrets. Source code: https://github.com/XXIDENT/shorts
> Privacy policy: https://github.com/XXIDENT/shorts/blob/main/PRIVACY.md

**Quota**: 기본 할당량(10,000)으로 충분하다고 적으세요. 추가 요청은 하지 않는 게 승인에 유리해요.

**스크린캐스트를 요구하면**: 화면 녹화로 (1) GitHub Actions에서 워크플로 실행 → (2) 로그에 업로드 완료 →
(3) YouTube Studio에 영상이 올라온 모습을 1~2분 보여 주면 됩니다.
