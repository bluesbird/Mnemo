package com.personalknowledgehub.knowledgeservice.knowledgehub.domain;

public class NoteNotFoundException extends RuntimeException {

    public NoteNotFoundException(Long id) {
        super("Note with id " + id + " does not exist");
    }
}
