package com.example.springbootrefresh.knowledgehub.api;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;

import java.util.List;

public record CreateNoteRequestDto(
        @NotBlank(message = "Title cannot be blank")
        String title,
        
        @NotBlank(message = "Content cannot be blank")
        String content,
        
        @NotEmpty(message = "At least one tag is required")
        List<String> tagNames
) {}
