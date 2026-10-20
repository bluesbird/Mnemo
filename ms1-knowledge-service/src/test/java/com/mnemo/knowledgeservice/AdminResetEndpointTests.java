package com.mnemo.knowledgeservice;

import com.mnemo.knowledgeservice.knowledgehub.domain.Note;
import com.mnemo.knowledgeservice.knowledgehub.api.AdminController;
import com.mnemo.knowledgeservice.knowledgehub.persistence.NoteRepository;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.web.server.ResponseStatusException;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

@SpringBootTest(properties = "app.reset.api-key=test-reset-key-that-is-long-enough-for-tests")
class AdminResetEndpointTests {

    @Autowired
    private AdminController adminController;

    @Autowired
    private NoteRepository noteRepository;

    @AfterEach
    void cleanup() {
        noteRepository.deleteAllInBatch();
    }

    @Test
    void resetRejectsMissingOrInvalidKey() {
        assertThrows(ResponseStatusException.class, () -> adminController.resetDatabase(null));
        assertThrows(ResponseStatusException.class, () -> adminController.resetDatabase("wrong"));
    }

    @Test
    void resetRestoresStarterNotes() {
        Note note = new Note("Legacy note", "Old content");
        noteRepository.save(note);

        var response = adminController.resetDatabase("test-reset-key-that-is-long-enough-for-tests");
        assertEquals(202, response.getStatusCode().value());
        assertEquals("reset", response.getBody().status());
        assertEquals(10, response.getBody().restoredNoteCount());
        assertEquals("queued", response.getBody().indexRebuild());

        long noteCount = noteRepository.count();
        long attentionCount = noteRepository.findAll().stream()
                .filter(stored -> "Attention Is All You Need".equals(stored.getTitle()))
                .count();

        assertEquals(10, noteCount);
        assertEquals(1, attentionCount);
    }
}
