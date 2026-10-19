package com.mnemo.knowledgeservice;

import com.mnemo.knowledgeservice.knowledgehub.api.dto.CreateNoteRequestDto;
import com.mnemo.knowledgeservice.knowledgehub.api.dto.UpdateNoteRequestDto;
import jakarta.validation.Validation;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class NoteRequestValidationTests {
    @Test
    void validatesCreateAndUpdateLengthBoundaries() {
        try (var factory = Validation.buildDefaultValidatorFactory()) {
            var validator = factory.getValidator();
            for (int extra = 0; extra <= 1; extra++) {
                String title = "t".repeat(100 + extra);
                String content = "c".repeat(5000 + extra);
                assertEquals(extra * 2,
                        validator.validate(new CreateNoteRequestDto(title, content)).size());
                assertEquals(extra * 2,
                        validator.validate(new UpdateNoteRequestDto(title, content)).size());
            }
        }
    }
}
