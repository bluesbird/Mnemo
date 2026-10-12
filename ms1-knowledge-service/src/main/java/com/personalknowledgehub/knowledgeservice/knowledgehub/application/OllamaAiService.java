package com.personalknowledgehub.knowledgeservice.knowledgehub.application;

import org.springframework.ai.chat.client.ChatClient;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.util.Arrays;
import java.util.List;
import java.util.Locale;

@Service
public class OllamaAiService {

    private static final Logger logger = LoggerFactory.getLogger(OllamaAiService.class);

    private final ChatClient chatClient;
    private final boolean enabled;

    public OllamaAiService(
            ChatClient.Builder chatClientBuilder,
            @Value("${ai.ollama.enabled:true}") boolean enabled
    ) {
        this.chatClient = chatClientBuilder.build();
        this.enabled = enabled;
    }

    public AiNoteEnrichment enrichNote(String title, String content) {
        if (!enabled) {
            return new AiNoteEnrichment(null, List.of());
        }

        try {
            String summaryPrompt = "Create a short summary of this note.\n"
                    + "Rules:\n"
                    + "- Start with \"This note ...\"\n"
                    + "- Keep it shorter than the original note\n"
                    + "- Maximum 1 sentence\n"
                    + "- Do not copy or repeat full phrases from the note\n"
                    + "- Return only the summary sentence\n\n"
                    + "Title: " + title + "\n"
                    + "Content: " + content;

            String tagsPrompt = "Generate up to 3 short lowercase tags for this note. "
                    + "Return ONLY comma-separated tags, no explanation.\n\n"
                    + "Title: " + title + "\n"
                    + "Content: " + content;

            String summary = toSummaryOrNull(callModel(summaryPrompt));
            String rawTags = callModel(tagsPrompt);
            List<String> parsedTags = parseTags(rawTags);

            return new AiNoteEnrichment(summary, parsedTags);
        } catch (RuntimeException ex) {
            logger.warn("Spring AI Ollama call failed ({}). Leaving summary and tags empty", ex.getMessage());
            return new AiNoteEnrichment(null, List.of());
        }
    }

    private String callModel(String prompt) {
        String response = chatClient.prompt(prompt).call().content();
        return response == null ? "" : response;
    }

    private String toSummaryOrNull(String rawSummary) {
        if (rawSummary == null) {
            return null;
        }

        String summary = rawSummary.replaceAll("\\s+", " ").trim();
        if (summary.isBlank()) {
            return null;
        }

        if (!summary.toLowerCase(Locale.ROOT).startsWith("this note")) {
            summary = "This note " + summary;
        }

        return summary;
    }

    private List<String> parseTags(String rawTags) {
        if (rawTags == null || rawTags.isBlank()) {
            return List.of();
        }

        return Arrays.stream(rawTags.split("[,\\n]"))
                .map(tag -> tag.replaceAll("^[\\-\\d\\.\\)\\s]+", ""))
                .map(tag -> tag.replaceAll("[^a-zA-Z0-9\\-\\s]", ""))
                .map(tag -> tag.trim().toLowerCase(Locale.ROOT))
                .filter(tag -> !tag.isBlank())
                .distinct()
                .limit(3)
                .toList();
    }

    public record AiNoteEnrichment(String summary, List<String> tagNames) {
    }
}
