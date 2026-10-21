package com.mnemo.knowledgeservice;

import com.mnemo.knowledgeservice.knowledgehub.domain.Note;
import com.mnemo.knowledgeservice.knowledgehub.persistence.NoteRepository;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.transaction.annotation.Transactional;

import jakarta.persistence.EntityManager;
import jakarta.persistence.PersistenceContext;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.stream.IntStream;

import static org.junit.jupiter.api.Assertions.assertEquals;

@SpringBootTest(properties = "app.events.outbox.enabled=false")
class NoteRepositoryTests {

    @Autowired
    private NoteRepository noteRepository;

    @PersistenceContext
    private EntityManager entityManager;

    @Test
    void noteLimitSerializesConcurrentCreatesAndDeletionFreesSpace() throws Exception {
        var fixtures = noteRepository.saveAll(IntStream.range(0, 99)
                .mapToObj(i -> new Note("Limit " + i, "Content")).toList());
        var created = new java.util.ArrayList<Note>();
        try (var executor = Executors.newFixedThreadPool(2)) {
            var first = executor.submit(() -> noteRepository.saveBelowLimit(new Note("First", "Content"), 100));
            var second = executor.submit(() -> noteRepository.saveBelowLimit(new Note("Second", "Content"), 100));
            var firstResult = first.get(10, TimeUnit.SECONDS);
            var secondResult = second.get(10, TimeUnit.SECONDS);
            firstResult.ifPresent(created::add);
            secondResult.ifPresent(created::add);
            assertEquals(1, created.size());
            assertEquals(100, noteRepository.count());
            noteRepository.delete(created.removeFirst());
            var replacement = noteRepository.saveBelowLimit(new Note("Replacement", "Content"), 100);
            replacement.ifPresent(created::add);
            assertEquals(true, replacement.isPresent());
        } finally {
            noteRepository.deleteAll(created);
            noteRepository.deleteAll(fixtures);
        }
    }

    @Test
    @Transactional
    void persistsNoteWithSummary() {
        Note note = new Note("Learning Spring", "Spring Boot fundamentals");
        note.setSummary("This note introduces Spring Boot.");
        
        Note saved = noteRepository.save(note);

        entityManager.flush();
        entityManager.clear();

        Note loaded = noteRepository.findById(saved.getId()).orElseThrow();
        assertEquals("Learning Spring", loaded.getTitle());
        assertEquals("Spring Boot fundamentals", loaded.getContent());
        assertEquals("This note introduces Spring Boot.", loaded.getSummary());
        assertEquals(computeExpectedSourceHash("Learning Spring", "Spring Boot fundamentals"), loaded.getSourceHash());
    }

    @Test
    @Transactional
    void sourceHashUpdatesWhenTitleOrContentChanges() {
        Note note = noteRepository.save(new Note("Original title", "Original content"));
        entityManager.flush();
        entityManager.clear();

        Note created = noteRepository.findById(note.getId()).orElseThrow();
        String initialHash = created.getSourceHash();
        assertEquals(computeExpectedSourceHash("Original title", "Original content"), initialHash);

        created.updateCoreContent("Updated title", "Updated content");
        noteRepository.save(created);
        entityManager.flush();
        entityManager.clear();

        Note updated = noteRepository.findById(note.getId()).orElseThrow();
        assertEquals(computeExpectedSourceHash("Updated title", "Updated content"), updated.getSourceHash());
    }

    private String computeExpectedSourceHash(String title, String content) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            digest.update("v1\0".getBytes(StandardCharsets.UTF_8));
            digest.update(title.getBytes(StandardCharsets.UTF_8));
            digest.update("\0".getBytes(StandardCharsets.UTF_8));
            digest.update(content.getBytes(StandardCharsets.UTF_8));
            byte[] hashBytes = digest.digest();
            StringBuilder hex = new StringBuilder(hashBytes.length * 2);
            for (byte hashByte : hashBytes) {
                hex.append(String.format("%02x", hashByte));
            }
            return hex.toString();
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException("SHA-256 is not available", e);
        }
    }
}
