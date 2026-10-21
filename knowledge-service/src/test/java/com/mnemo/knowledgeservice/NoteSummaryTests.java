package com.mnemo.knowledgeservice;

import com.mnemo.knowledgeservice.common.web.ApiExceptionHandler;
import com.mnemo.knowledgeservice.knowledgehub.application.NoteSummaryException;
import com.mnemo.knowledgeservice.knowledgehub.application.NoteService;
import com.mnemo.knowledgeservice.knowledgehub.application.NoteSummaryService;
import com.mnemo.knowledgeservice.knowledgehub.domain.Note;
import com.mnemo.knowledgeservice.knowledgehub.domain.NoteLimitReachedException;
import com.mnemo.knowledgeservice.knowledgehub.messaging.NoteEventPublisher;
import com.mnemo.knowledgeservice.knowledgehub.messaging.NoteEventType;
import com.mnemo.knowledgeservice.knowledgehub.persistence.NoteRepository;
import jakarta.servlet.http.HttpServletRequest;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.NullSource;
import org.junit.jupiter.params.provider.ValueSource;
import org.springframework.ai.chat.client.ChatClient;
import org.springframework.ai.chat.messages.AssistantMessage;
import org.springframework.ai.chat.metadata.ChatGenerationMetadata;
import org.springframework.ai.chat.model.ChatModel;
import org.springframework.ai.chat.model.ChatResponse;
import org.springframework.ai.chat.model.Generation;
import org.springframework.ai.chat.prompt.Prompt;
import org.springframework.ai.chat.prompt.ChatOptions;

import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

class NoteSummaryTests {

    private final ChatModel model = mock(ChatModel.class);
    private final NoteSummaryService service = new NoteSummaryService(ChatClient.builder(model), true);
    private final NoteRepository notes = mock(NoteRepository.class);
    private final NoteEventPublisher publisher = mock(NoteEventPublisher.class);
    private final NoteService noteService = new NoteService(notes, service, publisher);

    @BeforeEach
    void configureModelOptions() {
        when(model.getOptions()).thenReturn(ChatOptions.builder().build());
    }

    @Test
    void fullCollectionRejectsCreationWithoutPublishingAnEvent() {
        when(notes.saveBelowLimit(any(Note.class), eq(100))).thenReturn(Optional.empty());
        var error = assertThrows(NoteLimitReachedException.class,
                () -> noteService.addNote("Title", "Content"));
        var request = mock(HttpServletRequest.class);
        when(request.getRequestURI()).thenReturn("/api/v1/notes");
        var problem = new ApiExceptionHandler().handleNoteLimit(error, request);
        assertEquals(409, problem.getStatus());
        assertTrue(problem.getDetail().contains("100-note limit"));
        verifyNoInteractions(publisher);
    }

    @Test
    void summarizesWithOneModelCallAndDoesNotChangeIndexedContent() {
        when(model.call(any(Prompt.class))).thenReturn(response("A short summary.", "stop"));
        var note = existingNote();
        String sourceHash = note.getSourceHash();
        when(notes.save(note)).thenReturn(note);

        var result = noteService.summarizeNote(1L);

        assertEquals("This note A short summary.", result.getSummary());
        assertEquals("Title", result.getTitle());
        assertEquals("Content", result.getContent());
        assertEquals(sourceHash, result.getSourceHash());
        verify(model, times(1)).call(any(Prompt.class));
        verify(notes).save(note);
        verifyNoInteractions(publisher);
    }

    @Test
    void createAndUpdateNeverCallAiAndUpdateClearsSummary() {
        when(notes.save(any(Note.class))).thenAnswer(invocation -> invocation.getArgument(0));
        when(notes.saveBelowLimit(any(Note.class), eq(100)))
                .thenAnswer(invocation -> Optional.of(invocation.getArgument(0)));
        assertNull(noteService.addNote("New", "Content").getSummary());
        var note = existingNote();

        var updated = noteService.updateNote(1L, "Changed", "New content");

        assertNull(updated.getSummary());
        assertNull(note.getSummary());
        verify(model, never()).call(any(Prompt.class));
        verify(publisher).publish(NoteEventType.UPDATED, 1L);
    }

    @ParameterizedTest
    @NullSource
    @ValueSource(strings = {"", " ", "\n"})
    void rejectsEmptyAnswers(String answer) {
        when(model.call(any(Prompt.class))).thenReturn(response(answer, "stop"));

        assertThrows(NoteSummaryException.class, () -> service.summarizeNote("Title", "Content"));
    }

    @ParameterizedTest
    @NullSource
    @ValueSource(strings = {"length", "error", ""})
    void rejectsUnfinishedAnswersEvenWhenContentIsPresent(String finishReason) {
        when(model.call(any(Prompt.class))).thenReturn(response("Partial answer", finishReason));

        assertThrows(NoteSummaryException.class, () -> service.summarizeNote("Title", "Content"));
    }

    @Test
    void rejectsMissingGenerations() {
        when(model.call(any(Prompt.class))).thenReturn(new ChatResponse(List.of()));

        assertThrows(NoteSummaryException.class, () -> service.summarizeNote("Title", "Content"));
    }

    @Test
    void reportsUpstreamFailureInsteadOfReturningEmptySummary() {
        when(model.call(any(Prompt.class))).thenThrow(new IllegalStateException("connection failed"));

        var error = assertThrows(NoteSummaryException.class,
                () -> service.summarizeNote("Title", "Content"));

        assertEquals("connection failed", error.getCause().getMessage());
    }

    @Test
    void reportsDisabledSummarization() {
        var disabled = new NoteSummaryService(ChatClient.builder(model), false);

        assertThrows(NoteSummaryException.class, () -> disabled.summarizeNote("Title", "Content"));
        verifyNoInteractions(model);
    }

    @Test
    void failedSummaryPreservesExistingNoteAndDoesNotPublishEvents() {
        when(model.call(any(Prompt.class))).thenReturn(response("partial", "length"));
        var note = existingNote();
        var updatedAt = note.getUpdatedAt();

        assertThrows(NoteSummaryException.class, () -> noteService.summarizeNote(1L));

        assertEquals("Existing summary", note.getSummary());
        assertEquals(updatedAt, note.getUpdatedAt());
        verify(notes, never()).save(any(Note.class));
        verifyNoInteractions(publisher);
    }

    @Test
    void returnsProblemDetailWithBadGatewayStatus() {
        var request = mock(HttpServletRequest.class);
        when(request.getRequestURI()).thenReturn("/api/v1/notes/1/summarize");
        var problem = new ApiExceptionHandler().handleNoteSummary(
                new NoteSummaryException("Note summarization reached its token limit before finishing."),
                request
        );

        assertEquals(502, problem.getStatus());
        assertEquals("Note summarization failed", problem.getTitle());
        assertEquals("Note summarization reached its token limit before finishing.", problem.getDetail());
        assertEquals("/api/v1/notes/1/summarize", problem.getInstance().toString());
    }

    private Note existingNote() {
        var note = new Note("Title", "Content");
        note.setSummary("Existing summary");
        when(notes.findById(1L)).thenReturn(Optional.of(note));
        return note;
    }

    private static ChatResponse response(String content, String finishReason) {
        return new ChatResponse(List.of(new Generation(
                new AssistantMessage(content),
                ChatGenerationMetadata.builder().finishReason(finishReason).build()
        )));
    }
}
