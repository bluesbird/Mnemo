package com.mnemo.knowledgeservice;

import com.mnemo.knowledgeservice.knowledgehub.api.NoteController;
import com.mnemo.knowledgeservice.knowledgehub.application.NoteService;
import com.mnemo.knowledgeservice.knowledgehub.application.NoteIndexMetadata;
import com.mnemo.knowledgeservice.knowledgehub.domain.Note;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.test.json.JsonCompareMode;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import java.util.List;
import java.time.LocalDateTime;

import static org.mockito.Mockito.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

class NoteControllerTests {
    private final NoteService service = mock(NoteService.class);
    private final MockMvc mvc = MockMvcBuilders.standaloneSetup(new NoteController(service)).build();

    @Test
    void mapsCreateInputAndAllResponseFieldsWithoutExposingTheEntity() throws Exception {
        var note = note();
        when(service.addNote("Title", "Content")).thenReturn(note);

        mvc.perform(post("/api/v1/notes").contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"title":"Title","content":"Content"}
                                """))
                .andExpect(status().isCreated())
                .andExpect(header().string("Location", "http://localhost/api/v1/notes/1"))
                .andExpect(content().json("""
                        {"id":1,"title":"Title","content":"Content","summary":"Summary",
                         "sourceHash":"%s","createdAt":"%s","updatedAt":"%s"}
                        """.formatted(note.getSourceHash(), note.getCreatedAt(), note.getUpdatedAt()),
                        JsonCompareMode.STRICT));
        verify(service).addNote("Title", "Content");
    }

    @Test
    void mapsReadUpdateSummaryAndMetadataResponses() throws Exception {
        var note = note();
        when(service.getAllNotes()).thenReturn(List.of(note));
        when(service.getNoteById(1L)).thenReturn(note);
        when(service.getAllIndexMetadata()).thenReturn(
                List.of(new NoteIndexMetadata(note.getId(), note.getSourceHash())));
        when(service.updateNote(1L, "Title", "Content")).thenReturn(note);
        when(service.summarizeNote(1L)).thenReturn(note);

        mvc.perform(get("/api/v1/notes"))
                .andExpect(status().isOk()).andExpect(jsonPath("$[0].id").value(1));
        mvc.perform(get("/api/v1/notes/1"))
                .andExpect(status().isOk()).andExpect(jsonPath("$.title").value("Title"));
        mvc.perform(get("/api/v1/notes/index-metadata"))
                .andExpect(status().isOk())
                .andExpect(content().json("""
                        [{"noteId":1,"sourceHash":"%s"}]
                        """.formatted(note.getSourceHash()), JsonCompareMode.STRICT));
        mvc.perform(put("/api/v1/notes/1").contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"title":"Title","content":"Content"}
                                """))
                .andExpect(status().isOk()).andExpect(jsonPath("$.content").value("Content"));
        mvc.perform(post("/api/v1/notes/1/summarize"))
                .andExpect(status().isOk()).andExpect(jsonPath("$.summary").value("Summary"));
        verify(service).updateNote(1L, "Title", "Content");
    }

    @Test
    void validatesCreateAndUpdateBeforeCallingTheService() throws Exception {
        for (var request : List.of(post("/api/v1/notes"), put("/api/v1/notes/1"))) {
            mvc.perform(request.contentType(MediaType.APPLICATION_JSON)
                            .content("""
                                    {"title":"%s","content":"Content"}
                                    """.formatted("x".repeat(71))))
                    .andExpect(status().isBadRequest());
        }
        verifyNoInteractions(service);
    }

    private Note note() {
        var note = new Note("Title", "Content");
        ReflectionTestUtils.setField(note, "id", 1L);
        ReflectionTestUtils.setField(note, "createdAt", LocalDateTime.of(2026, 10, 21, 12, 0, 1));
        note.setUpdatedAt(LocalDateTime.of(2026, 10, 21, 13, 0, 1));
        note.setSummary("Summary");
        return note;
    }
}
