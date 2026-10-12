package com.personalknowledgehub.knowledgeservice.knowledgehub.api.dto;

import jakarta.validation.constraints.NotBlank;

public record UpdateNoteRequestDto(
        @NotBlank(message = "Title cannot be blank")
        String title,

        @NotBlank(message = "Content cannot be blank")
        String content
) {}
