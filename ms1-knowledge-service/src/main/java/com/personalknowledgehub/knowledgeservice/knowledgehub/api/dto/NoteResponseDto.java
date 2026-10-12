package com.personalknowledgehub.knowledgeservice.knowledgehub.api.dto;

import java.time.LocalDateTime;
import java.util.List;

public record NoteResponseDto(
        Long id,
        String title,
        String content,
        String summary,
        List<String> tags,
        LocalDateTime createdAt,
        LocalDateTime updatedAt
) {}
