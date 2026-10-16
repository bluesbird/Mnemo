package com.mnemo.knowledgeservice.knowledgehub.persistence;

import com.mnemo.knowledgeservice.knowledgehub.domain.Note;
import org.springframework.data.jpa.repository.JpaRepository;

public interface NoteRepository extends JpaRepository<Note, Long> {
    java.util.List<Note> findAllByOrderByIdAsc();
}
