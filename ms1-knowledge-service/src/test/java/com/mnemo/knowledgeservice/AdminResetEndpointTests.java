package com.mnemo.knowledgeservice;

import com.mnemo.knowledgeservice.knowledgehub.domain.Note;
import com.mnemo.knowledgeservice.knowledgehub.domain.Tag;
import com.mnemo.knowledgeservice.knowledgehub.api.AdminController;
import com.mnemo.knowledgeservice.knowledgehub.persistence.NoteRepository;
import com.mnemo.knowledgeservice.knowledgehub.persistence.TagRepository;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.server.ResponseStatusException;

import java.util.Set;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

@SpringBootTest(properties = "app.reset.api-key=test-reset-key-that-is-long-enough-for-tests")
class AdminResetEndpointTests {

    @Autowired
    private AdminController adminController;

    @Autowired
    private NoteRepository noteRepository;

    @Autowired
    private TagRepository tagRepository;

    @Autowired
    private JdbcTemplate jdbcTemplate;

    @AfterEach
    void cleanup() {
        jdbcTemplate.update("DELETE FROM note_tags");
        noteRepository.deleteAllInBatch();
        tagRepository.deleteAllInBatch();
    }

    @Test
    void resetRejectsMissingOrInvalidKey() {
        assertThrows(ResponseStatusException.class, () -> adminController.resetDatabase(null));
        assertThrows(ResponseStatusException.class, () -> adminController.resetDatabase("wrong"));
    }

    @Test
    void resetRestoresStarterNotesAndClearsTags() {
        Tag tag = tagRepository.save(new Tag("legacy"));
        Note note = new Note("Legacy note", "Old content");
        note.setTags(Set.of(tag));
        noteRepository.save(note);

        var response = adminController.resetDatabase("test-reset-key-that-is-long-enough-for-tests");
        assertEquals(202, response.getStatusCode().value());
        assertEquals("reset", response.getBody().status());
        assertEquals(10, response.getBody().restoredNoteCount());
        assertEquals("queued", response.getBody().indexRebuild());

        long noteCount = noteRepository.count();
        long tagCount = tagRepository.count();
        long attentionCount = noteRepository.findAll().stream()
                .filter(stored -> "Attention Is All You Need".equals(stored.getTitle()))
                .count();

        assertEquals(10, noteCount);
        assertEquals(0, tagCount);
        assertEquals(1, attentionCount);
    }
}
