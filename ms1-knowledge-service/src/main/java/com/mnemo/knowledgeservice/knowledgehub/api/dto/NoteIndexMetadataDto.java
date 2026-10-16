package com.mnemo.knowledgeservice.knowledgehub.api.dto;

public record NoteIndexMetadataDto(
        Long noteId,
        String sourceHash
) {
}
