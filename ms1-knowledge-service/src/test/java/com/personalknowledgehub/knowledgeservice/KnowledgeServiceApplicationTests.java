package com.personalknowledgehub.knowledgeservice;

import com.personalknowledgehub.knowledgeservice.knowledgehub.domain.Note;
import com.personalknowledgehub.knowledgeservice.knowledgehub.domain.Tag;
import com.personalknowledgehub.knowledgeservice.knowledgehub.persistence.NoteRepository;
import com.personalknowledgehub.knowledgeservice.knowledgehub.persistence.TagRepository;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.transaction.annotation.Transactional;

import jakarta.persistence.EntityManager;
import jakarta.persistence.PersistenceContext;
import java.util.HashSet;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

@SpringBootTest
class KnowledgeServiceApplicationTests {

    @Autowired
    private NoteRepository noteRepository;

    @Autowired
    private TagRepository tagRepository;

    @PersistenceContext
    private EntityManager entityManager;

    @Test
    void contextLoads() {
    }

    @Test
    @Transactional
    void persistsNoteWithTags() {
        Tag tag1 = tagRepository.save(new Tag("spring"));
        Tag tag2 = tagRepository.save(new Tag("java"));

        Note note = new Note("Learning Spring", "Spring Boot fundamentals");
        note.setTags(new HashSet<>(Set.of(tag1, tag2)));
        note.setSummary(null);
        
        Note saved = noteRepository.save(note);

        entityManager.flush();
        entityManager.clear();

        Note loaded = noteRepository.findById(saved.getId()).orElseThrow();
        assertEquals("Learning Spring", loaded.getTitle());
        assertEquals("Spring Boot fundamentals", loaded.getContent());
        assertNull(loaded.getSummary());
        assertEquals(2, loaded.getTags().size());
        assertTrue(loaded.getTags().stream().anyMatch(t -> t.getName().equals("spring")));
        assertTrue(loaded.getTags().stream().anyMatch(t -> t.getName().equals("java")));
    }

    @Test
    @Transactional
    void tagsAreSharedAcrossNotes() {
        Tag sharedTag = tagRepository.save(new Tag("ai"));

        Note note1 = new Note("AI Basics", "Introduction to AI");
        note1.setTags(new HashSet<>(Set.of(sharedTag)));
        noteRepository.save(note1);

        Note note2 = new Note("LLMs", "Large Language Models");
        note2.setTags(new HashSet<>(Set.of(sharedTag)));
        noteRepository.save(note2);

        entityManager.flush();
        entityManager.clear();

        Tag loaded = tagRepository.findByName("ai").orElseThrow();
        assertEquals(2, loaded.getNotes().size());
    }
}
