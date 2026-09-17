package com.example.mailauth.config;

import org.junit.jupiter.api.Test;
import org.springframework.mail.javamail.JavaMailSenderImpl;
import org.springframework.test.util.ReflectionTestUtils;
import static org.junit.jupiter.api.Assertions.*;

class EmailConfigTest {
    @Test
    void configuresSmtpTlsModesAndRejectsContradictions() {
        for (boolean[] mode : new boolean[][]{{false,false,false},{false,true,true},{true,false,false}}) {
            EmailConfig config = config(mode[0], mode[1], mode[2]);
            JavaMailSenderImpl sender = (JavaMailSenderImpl) config.javaMailSender();
            assertEquals(mode[0], sender.getJavaMailProperties().get("mail.smtp.ssl.enable"));
            assertEquals(mode[1], sender.getJavaMailProperties().get("mail.smtp.starttls.enable"));
            assertEquals(mode[2], sender.getJavaMailProperties().get("mail.smtp.starttls.required"));
            assertEquals(true, sender.getJavaMailProperties().get("mail.smtp.ssl.checkserveridentity"));
        }
        assertThrows(IllegalArgumentException.class, () -> config(true,true,true).javaMailSender());
        assertThrows(IllegalArgumentException.class, () -> config(false,false,true).javaMailSender());
    }

    private EmailConfig config(boolean ssl, boolean starttls, boolean required) {
        EmailConfig config = new EmailConfig();
        ReflectionTestUtils.setField(config,"host","smtp.example.invalid");
        ReflectionTestUtils.setField(config,"port",587);
        ReflectionTestUtils.setField(config,"ssl",ssl);
        ReflectionTestUtils.setField(config,"starttlsEnable",starttls);
        ReflectionTestUtils.setField(config,"starttlsRequired",required);
        return config;
    }
}
