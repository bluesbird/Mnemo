package com.mnemo.knowledgeservice.knowledgehub.application;

public class AiEnrichmentException extends RuntimeException {

    public AiEnrichmentException(String message) {
        super(message);
    }

    public AiEnrichmentException(String message, Throwable cause) {
        super(message, cause);
    }
}
