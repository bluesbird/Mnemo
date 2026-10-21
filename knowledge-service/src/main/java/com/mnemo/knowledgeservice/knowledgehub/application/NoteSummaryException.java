package com.mnemo.knowledgeservice.knowledgehub.application;

public class NoteSummaryException extends RuntimeException {

    public NoteSummaryException(String message) {
        super(message);
    }

    public NoteSummaryException(String message, Throwable cause) {
        super(message, cause);
    }
}
