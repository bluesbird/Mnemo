package com.mnemo.knowledgeservice.knowledgehub.persistence;

import com.mnemo.knowledgeservice.knowledgehub.domain.Note;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.transaction.annotation.Transactional;

import java.util.Optional;

public interface NoteRepository extends JpaRepository<Note, Long> {
    java.util.List<Note> findAllByOrderByIdAsc();

    @Modifying
    @Query(value = "LOCK TABLE note IN EXCLUSIVE MODE", nativeQuery = true)
    void lockForCreation();

    @Transactional
    default Optional<Note> saveBelowLimit(Note note, int limit) {
        // Serialize the count and insert across concurrent requests and service instances.
        lockForCreation();
        return count() >= limit ? Optional.empty() : Optional.of(save(note));
    }
}
