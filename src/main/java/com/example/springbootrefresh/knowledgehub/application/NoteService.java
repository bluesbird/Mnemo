package com.example.springbootrefresh.knowledgehub.application;

import com.example.springbootrefresh.knowledgehub.api.CreateNoteRequestDto;
import com.example.springbootrefresh.knowledgehub.api.NoteResponseDto;
import com.example.springbootrefresh.knowledgehub.api.UpdateNoteRequestDto;
import com.example.springbootrefresh.knowledgehub.domain.Note;
import com.example.springbootrefresh.knowledgehub.domain.NoteNotFoundException;
import com.example.springbootrefresh.knowledgehub.domain.Tag;
import com.example.springbootrefresh.knowledgehub.persistence.NoteRepository;
import com.example.springbootrefresh.knowledgehub.persistence.TagRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.stream.Collectors;

@Service
public class NoteService {

    private static final Logger logger = LoggerFactory.getLogger(NoteService.class);

    private final NoteRepository noteRepository;
    private final TagRepository tagRepository;

    public NoteService(NoteRepository noteRepository, TagRepository tagRepository) {
        this.noteRepository = noteRepository;
        this.tagRepository = tagRepository;
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
        
        Set<Tag> tags = request.tagNames().stream()
                .map(tagName -> tagRepository.findByName(tagName)
                        .orElseGet(() -> tagRepository.save(new Tag(tagName))))
                .collect(Collectors.toSet());
        
        note.setTags(tags);
        note.setSummary(null);
        
        Note savedNote = noteRepository.save(note);
        logger.info("Created note with id {}", savedNote.getId());
        return toDto(savedNote);
    }

    public NoteResponseDto getNoteById(Long id) {
        logger.info("Retrieving note with id {}", id);
        return toDto(findNote(id));
    }

    public NoteResponseDto updateNote(Long id, UpdateNoteRequestDto request) {
        Note note = findNote(id);
        
        note.setTitle(request.title());
        note.setContent(request.content());
        note.setUpdatedAt(LocalDateTime.now());
        
        if (request.tagNames() != null && !request.tagNames().isEmpty()) {
            Set<Tag> tags = request.tagNames().stream()
                    .map(tagName -> tagRepository.findByName(tagName)
                            .orElseGet(() -> tagRepository.save(new Tag(tagName))))
                    .collect(Collectors.toSet());
            note.setTags(tags);
        }
        
        Note updatedNote = noteRepository.save(note);
        logger.info("Updated note with id {}", id);
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

    private NoteResponseDto toDto(Note note) {
        List<String> tagNames = note.getTags().stream()
                .map(Tag::getName)
                .collect(Collectors.toList());
        
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
}
