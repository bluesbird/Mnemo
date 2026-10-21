package com.mnemo.knowledgeservice.knowledgehub.api;

import com.mnemo.knowledgeservice.knowledgehub.application.NoteService;
import com.mnemo.knowledgeservice.knowledgehub.domain.Note;
import com.mnemo.knowledgeservice.knowledgehub.api.dto.CreateNoteRequestDto;
import com.mnemo.knowledgeservice.knowledgehub.api.dto.NoteIndexMetadataDto;
import com.mnemo.knowledgeservice.knowledgehub.api.dto.NoteResponseDto;
import com.mnemo.knowledgeservice.knowledgehub.api.dto.UpdateNoteRequestDto;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.servlet.support.ServletUriComponentsBuilder;

import java.net.URI;
import java.util.List;

@RestController
@RequestMapping(value = "api/v1/notes", produces = MediaType.APPLICATION_JSON_VALUE)
@Tag(name = "Notes", description = "Note management and manual AI summary endpoints")
public class NoteController {

    private final NoteService noteService;

    public NoteController(NoteService noteService) {
        this.noteService = noteService;
    }

    @GetMapping
    @Operation(summary = "List all notes")
    public List<NoteResponseDto> getAllNotes() {
        return noteService.getAllNotes().stream().map(this::toDto).toList();
    }

    @GetMapping("/index-metadata")
    @Operation(summary = "List note index metadata for MS2 reconciliation")
    public List<NoteIndexMetadataDto> getAllIndexMetadata() {
        return noteService.getAllIndexMetadata().stream()
                .map(metadata -> new NoteIndexMetadataDto(metadata.noteId(), metadata.sourceHash()))
                .toList();
    }

    @GetMapping("/{id}")
    @Operation(summary = "Get note by ID")
    public NoteResponseDto getNoteById(@PathVariable Long id) {
        return toDto(noteService.getNoteById(id));
    }

    @PostMapping(consumes = MediaType.APPLICATION_JSON_VALUE)
    @Operation(summary = "Create note")
    public ResponseEntity<NoteResponseDto> addNote(
            @Valid @RequestBody CreateNoteRequestDto note
    ) {
        NoteResponseDto createdNote = toDto(noteService.addNote(note.title(), note.content()));
        URI location = ServletUriComponentsBuilder.fromCurrentRequest()
                .path("/{id}")
                .buildAndExpand(createdNote.id())
                .toUri();
        return ResponseEntity.created(location).body(createdNote);
    }

    @PutMapping(value = "/{id}", consumes = MediaType.APPLICATION_JSON_VALUE)
    @Operation(summary = "Update note")
    public ResponseEntity<NoteResponseDto> updateNote(
            @PathVariable Long id,
            @Valid @RequestBody UpdateNoteRequestDto note
    ) {
        NoteResponseDto updatedNote = toDto(noteService.updateNote(id, note.title(), note.content()));
        return ResponseEntity.ok(updatedNote);
    }

    @PostMapping("/{id}/summarize")
    @Operation(summary = "Generate an AI summary for a note on request")
    public ResponseEntity<NoteResponseDto> summarizeNote(@PathVariable Long id) {
        return ResponseEntity.ok(toDto(noteService.summarizeNote(id)));
    }

    @DeleteMapping("/{id}")
    @Operation(summary = "Delete note")
    public ResponseEntity<Void> deleteNote(@PathVariable Long id) {
        noteService.deleteNote(id);
        return ResponseEntity.noContent().build();
    }

    private NoteResponseDto toDto(Note note) {
        return new NoteResponseDto(
                note.getId(),
                note.getTitle(),
                note.getContent(),
                note.getSummary(),
                note.getSourceHash(),
                note.getCreatedAt(),
                note.getUpdatedAt()
        );
    }
}
