package com.example.mailauth.service;

import com.example.mailauth.exception.BusinessLogicException;
import com.example.mailauth.exception.ExceptionCode;
import jakarta.mail.internet.InternetAddress;
import org.springframework.beans.factory.annotation.Value;
import lombok.extern.slf4j.Slf4j;
import org.springframework.mail.SimpleMailMessage;
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Slf4j
@Service
@Transactional
public class MailService {

    private final JavaMailSender emailSender;
    private final String from;

    public MailService(JavaMailSender emailSender,
                       @Value("${fedops.mail.from-address}") String fromAddress,
                       @Value("${fedops.mail.from-name}") String fromName) {
        this.emailSender = emailSender;
        try {
            if (fromAddress.contains("\r") || fromAddress.contains("\n")
                    || fromName.contains("\r") || fromName.contains("\n")) {
                throw new IllegalArgumentException();
            }
            InternetAddress address = new InternetAddress(fromAddress, true);
            address.validate();
            if (!fromAddress.equals(address.getAddress())) throw new IllegalArgumentException();
            if (!fromName.isEmpty()) address.setPersonal(fromName, "UTF-8");
            this.from = address.toString();
        } catch (Exception e) {
            throw new IllegalArgumentException("Configure a single valid FEDOPS_MAIL_FROM_ADDRESS and a single-line FEDOPS_MAIL_FROM_NAME");
        }
    }

    public void sendEmail(String toEmail,
                          String title,
                          String text) {
        SimpleMailMessage emailForm = createEmailForm(toEmail, title, text);
        try {
            emailSender.send(emailForm);
        } catch (RuntimeException e) {
            log.warn("Email delivery failed ({})", e.getClass().getSimpleName());
            throw new BusinessLogicException(ExceptionCode.UNABLE_TO_SEND_EMAIL);
        }
    }

    private SimpleMailMessage createEmailForm(String toEmail,
                                             String title,
                                             String text) {
        SimpleMailMessage message = new SimpleMailMessage();
        message.setFrom(from);
        message.setTo(toEmail);
        message.setSubject(title);
        message.setText(text);

        return message;
    }
}
