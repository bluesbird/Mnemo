package com.example.springbootrefresh.knowledgehub.api;

import jakarta.validation.constraints.NotBlank;

import java.util.List;

public record UpdateNoteRequestDto(
        @NotBlank(message = "Title cannot be blank")
        String title,
        
        @NotBlank(message = "Content cannot be blank")
        String content,
        
        List<String> tagNames
) {}
