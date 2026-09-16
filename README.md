# FedOps Gateway

이 서비스는 **이메일 인증 전용 게이트웨이**입니다.
사용자는 인증 요청을 보내고, 수신한 인증 코드를 검증할 수 있습니다.

## Base URL

```bash
http://ccl.gachon.ac.kr:40016
```

## 엔드포인트

### 1) 이메일 인증 요청

이메일로 인증 코드를 발송합니다.

* **Method**: `POST`
* **URL**: `/members/emails/verification-requests`
* **Query**: `email` (필수)

#### 예시

```bash
curl -X POST \
  "$BASE/members/emails/verification-requests?email=gyom1204@gachon.ac.kr"
```

#### 응답 (예시)

성공 시 200/202 등으로 응답하며, 별도의 바디는 없습니다.

---

### 2) 인증 코드 검증

이메일과 코드를 확인합니다.

* **Method**: `GET`
* **URL**: `/members/emails/verifications`
* **Query**:

  * `email` (필수)
  * `code` (필수)

#### 예시

```bash
curl -X GET \
  "$BASE/members/emails/verifications?email=gyom1204@gachon.ac.kr&code=148662"
```

#### 응답

* 성공

```json
{"data":{"verified":true}}
```

* 실패

```json
{"data":{"verified":false}}
```

## 사용 팁

* `BASE` 환경변수로 베이스 URL을 관리하면 편리합니다:

  ```bash
  export BASE="http://ccl.gachon.ac.kr:40016"
  ```
* 인증 코드는 유효기간이 있을 수 있으니(서비스 정책에 따름) **수신 즉시 검증**을 권장합니다.
* 동일 이메일에 대한 과도한 요청은 제한될 수 있습니다(서비스 정책에 따름).

## 변경 이력

* 초기 목적(FL server pod 연결)에서 현재 **이메일 인증 파드**로 목적이 변경되었습니다.

