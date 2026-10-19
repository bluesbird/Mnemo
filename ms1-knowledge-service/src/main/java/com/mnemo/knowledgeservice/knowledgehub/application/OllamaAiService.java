package com.mnemo.knowledgeservice.knowledgehub.application;

import com.openai.errors.RateLimitException;
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
            throw new AiEnrichmentException("AI enrichment is disabled.");
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

            String summary = toSummary(callModel(summaryPrompt));
            String rawTags = callModel(tagsPrompt);
            List<String> parsedTags = parseTags(rawTags);
            if (parsedTags.isEmpty()) {
                throw new AiEnrichmentException("AI enrichment returned no usable tags. Please try again.");
            }

            return new AiNoteEnrichment(summary, parsedTags);
        } catch (AiEnrichmentException ex) {
            logger.warn("AI enrichment failed: {}", ex.getMessage());
            throw ex;
        } catch (RateLimitException ex) {
            logger.warn("AI provider quota exceeded");
            throw new AiEnrichmentException("AI provider quota exceeded. Please try again later.", ex);
        } catch (RuntimeException ex) {
            logger.warn("AI provider call failed ({})", ex.getClass().getSimpleName());
            throw new AiEnrichmentException("AI enrichment could not complete. Please try again.", ex);
        }
    }

    private String callModel(String prompt) {
        var response = chatClient.prompt(prompt).call().chatResponse();
        var result = response == null ? null : response.getResult();
        if (result == null) {
            throw new AiEnrichmentException("AI enrichment returned an empty answer. Please try again.");
        }
        String finishReason = result.getMetadata().getFinishReason();
        if ("length".equalsIgnoreCase(finishReason)) {
            throw new AiEnrichmentException("AI enrichment reached its token limit before finishing. Please try again.");
        }
        if (!"stop".equalsIgnoreCase(finishReason)) {
            throw new AiEnrichmentException("AI enrichment did not finish normally. Please try again.");
        }
        String content = result.getOutput().getText();
        if (content == null || content.isBlank()) {
            throw new AiEnrichmentException("AI enrichment returned an empty answer. Please try again.");
        }
        return content;
    }

    private String toSummary(String rawSummary) {
        String summary = rawSummary.replaceAll("\\s+", " ").trim();

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
