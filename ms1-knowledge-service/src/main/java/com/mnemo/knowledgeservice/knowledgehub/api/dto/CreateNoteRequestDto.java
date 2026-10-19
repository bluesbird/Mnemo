package com.mnemo.knowledgeservice.knowledgehub.api.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public record CreateNoteRequestDto(
        @NotBlank(message = "Title cannot be blank")
        @Size(max = 100, message = "Title must be at most 100 characters")
        String title,

        @NotBlank(message = "Content cannot be blank")
        @Size(max = 5000, message = "Content must be at most 5000 characters")
        String content
) {}
