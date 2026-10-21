package com.mnemo.knowledgeservice.knowledgehub.api.dto;

public record DatabaseResetResponseDto(
        String status,
        int restoredNoteCount,
        String indexRebuild
) {
}
