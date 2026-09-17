# fedops-gateway-onprem

온프레미스용 정제 소스와 설정 외부화 작업본입니다. 기존 Git 이력의 fork가 아닌 새 초기 이력입니다. 원본 라이선스와 저작자 표기를 유지합니다.

- 원본 범위·파일 해시: [SOURCE_PROVENANCE.json](SOURCE_PROVENANCE.json). 전달본은 일부 저장소의 부분 export입니다.
- 포함된 Dockerfile은 로컬 검증에 사용한 digest 기반 레시피입니다. .env·실제 자격정보는 포함하지 않습니다.
- 새 GitHub 주소를 Task Runtime이 사용하는 연결과 F/FL 검증은 아직 완료하지 않았습니다.
- 기존 upstream 자동 게시 workflow는 실행하지 않도록 이관에서 제외했습니다.
- 배포 설정: https://github.com/minsoojo/fedops-deployment

## SMTP·발신자 설정 (2026-09-17)

기존 JavaMailSender 발송과 Redis의 6자리 코드/30분 검증 흐름을 유지한다.
`FEDOPS_MAIL_FROM_ADDRESS`(생략 시 `SPRING_MAIL_USERNAME`), `FEDOPS_MAIL_FROM_NAME`(기본 FedOps)으로 From을 설정한다.
빈/잘못된 주소, 복수 주소, CR/LF를 거부하며 UTF-8 표시명을 지원한다.
SMTP 로그인은 `SPRING_MAIL_USERNAME/PASSWORD`, 서버·포트는 기존 환경변수로 받는다.
`SPRING_MAIL_PROPERTIES_MAIL_SMTP_SSL_ENABLE=true`는 implicit TLS용이며 STARTTLS 옵션 두 개는 false여야 한다.
SSL 및 STARTTLS에서는 서버 이름 검증을 활성화한다. 발송 실패 로그에 메일 본문/코드를 기록하지 않는다.

Dockerfile은 `gradle test bootJar`를 실행한다. Java 검사 4개 및 격리 Gateway/Redis/Mailpit에서 발신자 3개 구성의
SMTP 수신, 정상/오류 코드 검증과 TTL 검사를 통과했다. 실제 외부 SMTP 자격은 포함하지 않는다.
배포 저장소의 SMTP_CONFIGURATION.md와 Chart의 smtp.* / secrets.smtp를 사용한다.
