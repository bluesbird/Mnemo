package com.mnemo.knowledgeservice;

import com.mnemo.knowledgeservice.common.web.ApiExceptionHandler;
import com.mnemo.knowledgeservice.knowledgehub.application.AiEnrichmentException;
import com.mnemo.knowledgeservice.knowledgehub.application.NoteService;
import com.mnemo.knowledgeservice.knowledgehub.application.OllamaAiService;
import com.mnemo.knowledgeservice.knowledgehub.domain.Note;
import com.mnemo.knowledgeservice.knowledgehub.domain.Tag;
import com.mnemo.knowledgeservice.knowledgehub.messaging.NoteEventPublisher;
import com.mnemo.knowledgeservice.knowledgehub.persistence.NoteRepository;
import com.mnemo.knowledgeservice.knowledgehub.persistence.TagRepository;
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
import java.util.Set;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

class AiEnrichmentTests {

    private final ChatModel model = mock(ChatModel.class);
    private final OllamaAiService service = new OllamaAiService(ChatClient.builder(model), true);

    @BeforeEach
    void configureModelOptions() {
        when(model.getOptions()).thenReturn(ChatOptions.builder().build());
    }

    @Test
    void enrichesWithCompleteSummaryAndTags() {
        when(model.call(any(Prompt.class))).thenReturn(
                response("A short summary.", "stop"),
                response("Gardening, CACTUS, gardening", "stop")
        );

        var result = service.enrichNote("Title", "Content");

        assertEquals("This note A short summary.", result.summary());
        assertEquals(List.of("gardening", "cactus"), result.tagNames());
    }

    @ParameterizedTest
    @NullSource
    @ValueSource(strings = {"", " ", "\n"})
    void rejectsEmptyAnswers(String answer) {
        when(model.call(any(Prompt.class))).thenReturn(response(answer, "stop"));

        assertThrows(AiEnrichmentException.class, () -> service.enrichNote("Title", "Content"));
    }

    @ParameterizedTest
    @NullSource
    @ValueSource(strings = {"length", "error", ""})
    void rejectsUnfinishedAnswersEvenWhenContentIsPresent(String finishReason) {
        when(model.call(any(Prompt.class))).thenReturn(response("Partial answer", finishReason));

        assertThrows(AiEnrichmentException.class, () -> service.enrichNote("Title", "Content"));
    }

    @Test
    void rejectsMissingGenerations() {
        when(model.call(any(Prompt.class))).thenReturn(new ChatResponse(List.of()));

        assertThrows(AiEnrichmentException.class, () -> service.enrichNote("Title", "Content"));
    }

    @Test
    void rejectsUnusableTags() {
        when(model.call(any(Prompt.class))).thenReturn(
                response("This note is about gardening.", "stop"),
                response("!!!", "stop")
        );

        assertThrows(AiEnrichmentException.class, () -> service.enrichNote("Title", "Content"));
    }

    @Test
    void reportsUpstreamFailureInsteadOfReturningEmptyEnrichment() {
        when(model.call(any(Prompt.class))).thenThrow(new IllegalStateException("connection failed"));

        var error = assertThrows(AiEnrichmentException.class,
                () -> service.enrichNote("Title", "Content"));

        assertEquals("connection failed", error.getCause().getMessage());
    }

    @Test
    void reportsDisabledEnrichmentInsteadOfClearingFields() {
        var disabled = new OllamaAiService(ChatClient.builder(model), false);

        assertThrows(AiEnrichmentException.class, () -> disabled.enrichNote("Title", "Content"));
        verifyNoInteractions(model);
    }

    @Test
    void failedTagsCallPreservesExistingNoteAndDoesNotPublishEvents() {
        when(model.call(any(Prompt.class))).thenReturn(
                response("This note has a new summary.", "stop"),
                response("partial", "length")
        );
        var notes = mock(NoteRepository.class);
        var tags = mock(TagRepository.class);
        var publisher = mock(NoteEventPublisher.class);
        var note = new Note("Title", "Content");
        note.setSummary("Existing summary");
        var existingTags = Set.of(new Tag("existing"));
        note.setTags(existingTags);
        var updatedAt = note.getUpdatedAt();
        when(notes.findById(1L)).thenReturn(Optional.of(note));
        var noteService = new NoteService(notes, tags, service, publisher);

        assertThrows(AiEnrichmentException.class, () -> noteService.enrichNoteWithAi(1L));

        assertEquals("Existing summary", note.getSummary());
        assertEquals(existingTags, note.getTags());
        assertEquals(updatedAt, note.getUpdatedAt());
        verify(notes, never()).save(any(Note.class));
        verifyNoInteractions(tags, publisher);
    }

    @Test
    void returnsProblemDetailWithBadGatewayStatus() {
        var request = mock(HttpServletRequest.class);
        when(request.getRequestURI()).thenReturn("/api/v1/notes/1/ai-enrich");
        var problem = new ApiExceptionHandler().handleAiEnrichment(
                new AiEnrichmentException("AI enrichment reached its token limit before finishing."),
                request
        );

        assertEquals(502, problem.getStatus());
        assertEquals("AI enrichment failed", problem.getTitle());
        assertEquals("AI enrichment reached its token limit before finishing.", problem.getDetail());
        assertEquals("/api/v1/notes/1/ai-enrich", problem.getInstance().toString());
    }

    private static ChatResponse response(String content, String finishReason) {
        return new ChatResponse(List.of(new Generation(
                new AssistantMessage(content),
                ChatGenerationMetadata.builder().finishReason(finishReason).build()
        )));
    }
}
