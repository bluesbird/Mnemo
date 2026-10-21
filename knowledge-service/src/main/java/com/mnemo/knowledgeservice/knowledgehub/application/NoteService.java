package com.mnemo.knowledgeservice.knowledgehub.application;

import com.mnemo.knowledgeservice.knowledgehub.domain.Note;
import com.mnemo.knowledgeservice.knowledgehub.domain.NoteLimitReachedException;
import com.mnemo.knowledgeservice.knowledgehub.domain.NoteNotFoundException;
import com.mnemo.knowledgeservice.knowledgehub.messaging.NoteEventPublisher;
import com.mnemo.knowledgeservice.knowledgehub.messaging.NoteEventType;
import com.mnemo.knowledgeservice.knowledgehub.persistence.NoteRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

@Service
public class NoteService {

    private static final Logger logger = LoggerFactory.getLogger(NoteService.class);

    private final NoteRepository noteRepository;
    private final NoteSummaryService noteSummaryService;
    private final NoteEventPublisher noteEventPublisher;

    public NoteService(
            NoteRepository noteRepository,
            NoteSummaryService noteSummaryService,
            NoteEventPublisher noteEventPublisher
    ) {
        this.noteRepository = noteRepository;
        this.noteSummaryService = noteSummaryService;
        this.noteEventPublisher = noteEventPublisher;
    }

    public List<Note> getAllNotes() {
        List<Note> notes = noteRepository.findAll();
        logger.info("Retrieved {} notes", notes.size());
        return notes;
    }

    @Transactional
    public Note addNote(String title, String content) {
        Note note = new Note(title, content);
        note.setSummary(null);

        Note savedNote = noteRepository.saveBelowLimit(note, 100).orElseThrow(() -> {
            logger.warn("Note creation rejected: the 100-note limit has been reached");
            return new NoteLimitReachedException();
        });
        logger.info("Created note with id {}", savedNote.getId());
        noteEventPublisher.publish(NoteEventType.CREATED, savedNote.getId());
        return savedNote;
    }

    public Note getNoteById(Long id) {
        logger.info("Retrieving note with id {}", id);
        return findNote(id);
    }

    public List<NoteIndexMetadata> getAllIndexMetadata() {
        List<Note> notes = noteRepository.findAllByOrderByIdAsc();
        backfillMissingIndexMetadata(notes);

        logger.info("Retrieved index metadata for {} notes", notes.size());
        return notes.stream()
                .map(note -> new NoteIndexMetadata(note.getId(), note.getSourceHash()))
                .toList();
    }

    @Transactional
    public Note updateNote(Long id, String title, String content) {
        Note note = findNote(id);

        note.updateCoreContent(title, content);
        note.setSummary(null);
        note.setUpdatedAt(LocalDateTime.now());

        Note updatedNote = noteRepository.save(note);
        logger.info("Updated note with id {}", id);
        noteEventPublisher.publish(NoteEventType.UPDATED, id);
        return updatedNote;
    }

    public Note summarizeNote(Long id) {
        Note note = findNote(id);

        String summary = noteSummaryService.summarizeNote(
                note.getTitle(),
                note.getContent()
        );

        note.setSummary(summary);
        note.setUpdatedAt(LocalDateTime.now());

        Note updatedNote = noteRepository.save(note);
        logger.info("Summarized note with id {}", id);
        return updatedNote;
    }

    @Transactional
    public void deleteNote(Long id) {
        noteRepository.delete(findNote(id));
        logger.info("Deleted note with id {}", id);
        noteEventPublisher.publish(NoteEventType.DELETED, id);
    }

    private Note findNote(Long id) {
        return noteRepository.findById(id).orElseThrow(
                () -> {
                    logger.warn("Note with id {} was not found", id);
                    return new NoteNotFoundException(id);
                }
        );
    }

    private void backfillMissingIndexMetadata(List<Note> notes) {
        List<Note> notesToBackfill = new ArrayList<>();
        for (Note note : notes) {
            if (note.initializeIndexMetadataIfMissing()) {
                notesToBackfill.add(note);
            }
        }
        if (!notesToBackfill.isEmpty()) {
            noteRepository.saveAll(notesToBackfill);
            logger.info("Backfilled index metadata for {} notes", notesToBackfill.size());
        }
    }
}
