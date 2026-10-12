package com.example.springbootrefresh.knowledgehub.api;

import jakarta.validation.constraints.NotBlank;

public record CreateNoteRequestDto(
        @NotBlank(message = "Title cannot be blank")
        String title,

        @NotBlank(message = "Content cannot be blank")
        String content
) {}
