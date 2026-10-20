package com.mnemo.knowledgeservice.knowledgehub.application;

import com.mnemo.knowledgeservice.knowledgehub.domain.Note;
import com.mnemo.knowledgeservice.knowledgehub.messaging.NoteEventPublisher;
import com.mnemo.knowledgeservice.knowledgehub.messaging.NoteEventType;
import com.mnemo.knowledgeservice.knowledgehub.persistence.NoteRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class DatabaseResetService {

    private final NoteRepository noteRepository;
    private final StarterNoteCatalog starterNoteCatalog;
    private final NoteEventPublisher noteEventPublisher;

    public DatabaseResetService(
            NoteRepository noteRepository,
            StarterNoteCatalog starterNoteCatalog,
            NoteEventPublisher noteEventPublisher
    ) {
        this.noteRepository = noteRepository;
        this.starterNoteCatalog = starterNoteCatalog;
        this.noteEventPublisher = noteEventPublisher;
    }

    @Transactional
    public int reset() {
        noteRepository.deleteAllInBatch();

        var notes = starterNoteCatalog.notes().stream()
                .map(starter -> new Note(starter.title(), starter.content()))
                .toList();
        noteRepository.saveAll(notes);
        noteEventPublisher.publish(NoteEventType.INDEX_REBUILD_REQUESTED, null);
        return notes.size();
    }
}
