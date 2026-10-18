package com.mnemo.knowledgeservice.knowledgehub.application;

import com.mnemo.knowledgeservice.knowledgehub.domain.Note;
import com.mnemo.knowledgeservice.knowledgehub.messaging.NoteEventPublisher;
import com.mnemo.knowledgeservice.knowledgehub.messaging.NoteEventType;
import com.mnemo.knowledgeservice.knowledgehub.persistence.NoteRepository;
import com.mnemo.knowledgeservice.knowledgehub.persistence.TagRepository;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class DatabaseResetService {

    private final JdbcTemplate jdbcTemplate;
    private final NoteRepository noteRepository;
    private final TagRepository tagRepository;
    private final StarterNoteCatalog starterNoteCatalog;
    private final NoteEventPublisher noteEventPublisher;

    public DatabaseResetService(
            JdbcTemplate jdbcTemplate,
            NoteRepository noteRepository,
            TagRepository tagRepository,
            StarterNoteCatalog starterNoteCatalog,
            NoteEventPublisher noteEventPublisher
    ) {
        this.jdbcTemplate = jdbcTemplate;
        this.noteRepository = noteRepository;
        this.tagRepository = tagRepository;
        this.starterNoteCatalog = starterNoteCatalog;
        this.noteEventPublisher = noteEventPublisher;
    }

    @Transactional
    public int reset() {
        jdbcTemplate.update("DELETE FROM note_tags");
        noteRepository.deleteAllInBatch();
        tagRepository.deleteAllInBatch();

        var notes = starterNoteCatalog.notes().stream()
                .map(starter -> new Note(starter.title(), starter.content()))
                .toList();
        noteRepository.saveAll(notes);
        noteEventPublisher.publish(NoteEventType.INDEX_REBUILD_REQUESTED, null);
        return notes.size();
    }
}
