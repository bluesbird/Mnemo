package com.example.springbootrefresh.knowledgehub.persistence;

import com.example.springbootrefresh.knowledgehub.domain.Note;
import org.springframework.data.jpa.repository.JpaRepository;

public interface NoteRepository extends JpaRepository<Note, Long> {
}
