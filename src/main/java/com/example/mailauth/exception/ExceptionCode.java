package com.example.mailauth.exception;

import lombok.Getter;

@Getter
public enum ExceptionCode {
    MEMBER_EXISTS(409, "이미 존재하는 회원입니다."),
    UNABLE_TO_SEND_EMAIL(500, "이메일 전송에 실패했습니다."),
    NO_SUCH_ALGORITHM(500, "인증 코드 생성에 실패했습니다.");
    
    private final int status;
    private final String message;
    
    ExceptionCode(int status, String message) {
        this.status = status;
        this.message = message;
    }
}
