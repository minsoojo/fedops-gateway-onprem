package com.example.mailauth.dto;

import lombok.AllArgsConstructor;
import lombok.Getter;

@Getter
@AllArgsConstructor
public class EmailVerificationResult {
    private boolean verified;
    
    public static EmailVerificationResult of(boolean verified) {
        return new EmailVerificationResult(verified);
    }
}
