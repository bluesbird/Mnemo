package com.mnemo.knowledgeservice.knowledgehub.api.dto;

import java.time.LocalDateTime;

public record NoteResponseDto(
        Long id,
        String title,
        String content,
        String summary,
        String sourceHash,
        LocalDateTime createdAt,
        LocalDateTime updatedAt
) {}
