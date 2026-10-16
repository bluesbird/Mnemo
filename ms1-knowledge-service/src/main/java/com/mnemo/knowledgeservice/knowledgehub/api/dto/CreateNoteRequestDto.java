package com.mnemo.knowledgeservice.knowledgehub.api.dto;

import jakarta.validation.constraints.NotBlank;

public record CreateNoteRequestDto(
        @NotBlank(message = "Title cannot be blank")
        String title,

        @NotBlank(message = "Content cannot be blank")
        String content
) {}
