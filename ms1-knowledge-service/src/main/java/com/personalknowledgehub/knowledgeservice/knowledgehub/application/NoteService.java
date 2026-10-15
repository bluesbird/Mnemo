package com.personalknowledgehub.knowledgeservice.knowledgehub.application;

import com.personalknowledgehub.knowledgeservice.knowledgehub.api.dto.CreateNoteRequestDto;
import com.personalknowledgehub.knowledgeservice.knowledgehub.api.dto.NoteIndexMetadataDto;
import com.personalknowledgehub.knowledgeservice.knowledgehub.api.dto.NoteResponseDto;
import com.personalknowledgehub.knowledgeservice.knowledgehub.api.dto.UpdateNoteRequestDto;
import com.personalknowledgehub.knowledgeservice.knowledgehub.domain.Note;
import com.personalknowledgehub.knowledgeservice.knowledgehub.domain.NoteNotFoundException;
import com.personalknowledgehub.knowledgeservice.knowledgehub.domain.Tag;
import com.personalknowledgehub.knowledgeservice.knowledgehub.persistence.NoteRepository;
import com.personalknowledgehub.knowledgeservice.knowledgehub.persistence.TagRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;
import java.util.stream.Collectors;

@Service
public class NoteService {

    private static final Logger logger = LoggerFactory.getLogger(NoteService.class);

    private final NoteRepository noteRepository;
    private final TagRepository tagRepository;
    private final OllamaAiService ollamaAiService;

    public NoteService(
            NoteRepository noteRepository,
            TagRepository tagRepository,
            OllamaAiService ollamaAiService
    ) {
        this.noteRepository = noteRepository;
        this.tagRepository = tagRepository;
        this.ollamaAiService = ollamaAiService;
    }

    public List<NoteResponseDto> getAllNotes() {
        List<NoteResponseDto> notes = noteRepository.findAll().stream()
                .map(this::toDto)
                .toList();
        logger.info("Retrieved {} notes", notes.size());
        return notes;
    }

    public NoteResponseDto addNote(CreateNoteRequestDto request) {
        Note note = new Note(request.title(), request.content());
        note.setTags(new LinkedHashSet<>());
        note.setSummary(null);

        Note savedNote = noteRepository.save(note);
        logger.info("Created note with id {}", savedNote.getId());
        return toDto(savedNote);
    }

    public NoteResponseDto getNoteById(Long id) {
        logger.info("Retrieving note with id {}", id);
        return toDto(findNote(id));
    }

    public List<NoteIndexMetadataDto> getAllIndexMetadata() {
        List<Note> notes = noteRepository.findAllByOrderByIdAsc();
        backfillMissingIndexMetadata(notes);

        List<NoteIndexMetadataDto> metadata = notes.stream()
                .map(note -> new NoteIndexMetadataDto(
                        note.getId(),
                        note.getSourceHash()
                ))
                .toList();
        logger.info("Retrieved index metadata for {} notes", metadata.size());
        return metadata;
    }

    public NoteResponseDto updateNote(Long id, UpdateNoteRequestDto request) {
        Note note = findNote(id);

        note.updateCoreContent(request.title(), request.content());
        note.setSummary(null);
        note.setTags(new LinkedHashSet<>());
        note.setUpdatedAt(LocalDateTime.now());

        Note updatedNote = noteRepository.save(note);
        logger.info("Updated note with id {}", id);
        return toDto(updatedNote);
    }

    public NoteResponseDto enrichNoteWithAi(Long id) {
        Note note = findNote(id);

        OllamaAiService.AiNoteEnrichment enrichment = ollamaAiService.enrichNote(
                note.getTitle(),
                note.getContent()
        );

        note.setSummary(enrichment.summary());
        note.setTags(resolveTags(enrichment.tagNames()));
        note.setUpdatedAt(LocalDateTime.now());

        Note updatedNote = noteRepository.save(note);
        logger.info("AI-enriched note with id {}", id);
        return toDto(updatedNote);
    }

    public void deleteNote(Long id) {
        noteRepository.delete(findNote(id));
        logger.info("Deleted note with id {}", id);
    }

    private Note findNote(Long id) {
        return noteRepository.findById(id).orElseThrow(
                () -> {
                    logger.warn("Note with id {} was not found", id);
                    return new NoteNotFoundException(id);
                }
        );
    }

    private Set<Tag> resolveTags(List<String> tagNames) {
        if (tagNames == null || tagNames.isEmpty()) {
            return new LinkedHashSet<>();
        }

        return tagNames.stream()
                .map(tagName -> tagName == null ? "" : tagName.trim().toLowerCase())
                .filter(tagName -> !tagName.isBlank())
                .map(tagName -> tagRepository.findByName(tagName)
                        .orElseGet(() -> tagRepository.save(new Tag(tagName))))
                .collect(Collectors.toCollection(LinkedHashSet::new));
    }

    private NoteResponseDto toDto(Note note) {
        List<String> tagNames = note.getTags().stream()
                .map(Tag::getName)
                .sorted()
                .toList();

        return new NoteResponseDto(
                note.getId(),
                note.getTitle(),
                note.getContent(),
                note.getSummary(),
                tagNames,
                note.getCreatedAt(),
                note.getUpdatedAt()
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
