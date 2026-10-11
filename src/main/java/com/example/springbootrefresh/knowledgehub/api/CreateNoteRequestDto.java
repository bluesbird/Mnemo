package com.example.springbootrefresh.knowledgehub.api;

import java.util.List;

public record CreateNoteRequestDto(
        String title,
        String content,
        List<String> tagNames
) {}
