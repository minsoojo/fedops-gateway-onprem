package com.example.mailauth.controller;

import com.example.mailauth.dto.EmailVerificationResult;
import com.example.mailauth.dto.SingleResponseDto;
import com.example.mailauth.service.MemberService;
import com.example.mailauth.validation.CustomEmail;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import jakarta.validation.Valid;

@Slf4j
@RestController
@RequestMapping("/members")
@RequiredArgsConstructor
@Validated
public class MemberController {
    
    private final MemberService memberService;

    @PostMapping("/emails/verification-requests")
    public ResponseEntity<Void> sendMessage(@RequestParam("email") @Valid @CustomEmail String email) {
        memberService.sendCodeToEmail(email);
        return new ResponseEntity<>(HttpStatus.OK);
    }

    @GetMapping("/emails/verifications")
    public ResponseEntity<SingleResponseDto<EmailVerificationResult>> verificationEmail(
            @RequestParam("email") @Valid @CustomEmail String email,
            @RequestParam("code") String authCode) {
        EmailVerificationResult response = memberService.verifiedCode(email, authCode);
        return new ResponseEntity<>(new SingleResponseDto<>(response), HttpStatus.OK);
    }
}
