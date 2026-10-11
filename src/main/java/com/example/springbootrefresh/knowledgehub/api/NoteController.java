package com.example.springbootrefresh.knowledgehub.api;

import com.example.springbootrefresh.knowledgehub.application.NoteService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.servlet.support.ServletUriComponentsBuilder;
import org.springframework.web.bind.annotation.*;

import java.net.URI;
import java.util.List;

@RestController
@RequestMapping("api/v1/notes")
public class NoteController {

    private final NoteService noteService;

    public NoteController(NoteService noteService) {
        this.noteService = noteService;
    }

    @GetMapping
    public List<NoteResponseDto> getAllNotes() {
        return noteService.getAllNotes();
    }

    @GetMapping("/{id}")
    public NoteResponseDto getNoteById(@PathVariable Long id) {
        return noteService.getNoteById(id);
    }

    @PostMapping
    public ResponseEntity<NoteResponseDto> addNote(
            @RequestBody CreateNoteRequestDto note
    ) {
        NoteResponseDto createdNote = noteService.addNote(note);
        URI location = ServletUriComponentsBuilder.fromCurrentRequest()
                .path("/{id}")
                .buildAndExpand(createdNote.id())
                .toUri();
        return ResponseEntity.created(location).body(createdNote);
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteNote(@PathVariable Long id) {
        noteService.deleteNote(id);
        return ResponseEntity.noContent().build();
    }
}
