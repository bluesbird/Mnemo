package com.mnemo.knowledgeservice.knowledgehub.messaging;

public enum NoteEventType {
    CREATED("NoteCreated", "note.created"),
    UPDATED("NoteUpdated", "note.updated"),
    DELETED("NoteDeleted", "note.deleted");

    private final String eventType;
    private final String routingKey;

    NoteEventType(String eventType, String routingKey) {
        this.eventType = eventType;
        this.routingKey = routingKey;
    }

    public String eventType() {
        return eventType;
    }

    public String routingKey() {
        return routingKey;
    }
}
