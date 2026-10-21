package com.mnemo.knowledgeservice.knowledgehub.domain;

public class NoteLimitReachedException extends RuntimeException {
    public NoteLimitReachedException() {
        super("The 100-note limit has been reached. Delete a note before adding another.");
    }
}
