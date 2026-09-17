package com.example.mailauth.service;

import com.example.mailauth.exception.BusinessLogicException;
import jakarta.mail.internet.InternetAddress;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.mail.MailSendException;
import org.springframework.mail.SimpleMailMessage;
import org.springframework.mail.javamail.JavaMailSender;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class MailServiceTest {
    @Test
    void sendsConfiguredAddressAndUtf8NameWithoutChangingMessage() throws Exception {
        JavaMailSender sender = mock(JavaMailSender.class);
        new MailService(sender, "noreply@example.com", "페드옵스").sendEmail("test@example.com", "Verify", "test code");
        ArgumentCaptor<SimpleMailMessage> sent = ArgumentCaptor.forClass(SimpleMailMessage.class);
        verify(sender).send(sent.capture());
        SimpleMailMessage message = sent.getValue();
        InternetAddress from = new InternetAddress(message.getFrom());
        assertEquals("noreply@example.com", from.getAddress());
        assertEquals("페드옵스", from.getPersonal());
        assertArrayEquals(new String[]{"test@example.com"}, message.getTo());
        assertEquals("Verify", message.getSubject());
        assertEquals("test code", message.getText());
    }

    @Test
    void rejectsInvalidAndInjectedSenderConfiguration() {
        JavaMailSender sender = mock(JavaMailSender.class);
        for (String address : new String[]{"", "root", "a@example.com,b@example.com", "Name <a@example.com>", "a@example.com\r\nBcc: b@example.com"}) {
            assertThrows(IllegalArgumentException.class, () -> new MailService(sender, address, "FedOps"));
        }
        assertThrows(IllegalArgumentException.class, () -> new MailService(sender, "a@example.com", "Name\nInjected"));
    }

    @Test
    void keepsDeliveryFailureContract() {
        JavaMailSender sender = mock(JavaMailSender.class);
        doThrow(new MailSendException("test failure")).when(sender).send(any(SimpleMailMessage.class));
        assertThrows(BusinessLogicException.class, () -> new MailService(sender, "a@example.com", "")
                .sendEmail("test@example.com", "Verify", "test code"));
    }
}
