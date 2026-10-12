package com.example.springbootrefresh.knowledgehub.application;

import org.springframework.ai.chat.client.ChatClient;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.util.Arrays;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

@Service
public class OllamaAiService {

    private static final Logger logger = LoggerFactory.getLogger(OllamaAiService.class);
    private static final Pattern WORD_PATTERN = Pattern.compile("[A-Za-z][A-Za-z0-9-]*");
    private static final Set<String> STOP_WORDS = Set.of(
            "the", "and", "for", "with", "this", "that", "from", "into", "your", "have", "has",
            "are", "was", "were", "not", "but", "you", "our", "their", "will", "can", "use"
    );

    private final ChatClient chatClient;
    private final boolean enabled;
    private final boolean stubFallbackEnabled;

    public OllamaAiService(
            ChatClient.Builder chatClientBuilder,
            @Value("${ai.ollama.enabled:true}") boolean enabled,
            @Value("${ai.ollama.stub-fallback-enabled:true}") boolean stubFallbackEnabled
    ) {
        this.chatClient = chatClientBuilder.build();
        this.enabled = enabled;
        this.stubFallbackEnabled = stubFallbackEnabled;
    }

    public AiNoteEnrichment enrichNote(String title, String content) {
        if (!enabled) {
            return stubFallbackEnabled ? stubEnrichment(content) : new AiNoteEnrichment("", List.of());
        }

        try {
            String summaryPrompt = "Summarize the note in 2 concise sentences.\n\n"
                    + "Title: " + title + "\n"
                    + "Content: " + content;

            String tagsPrompt = "Generate up to 5 short lowercase tags for this note. "
                    + "Return ONLY comma-separated tags, no explanation.\n\n"
                    + "Title: " + title + "\n"
                    + "Content: " + content;

            String summary = callModel(summaryPrompt);
            String rawTags = callModel(tagsPrompt);
            List<String> parsedTags = parseTags(rawTags);

            if (summary == null || summary.isBlank() || parsedTags.isEmpty()) {
                logger.warn("Ollama response incomplete; using fallback enrichment");
                return stubFallbackEnabled ? stubEnrichment(content) : new AiNoteEnrichment("", List.of());
            }

            return new AiNoteEnrichment(summary.trim(), parsedTags);
        } catch (RuntimeException ex) {
            logger.warn("Spring AI Ollama call failed ({}). Falling back to enrichment stub", ex.getMessage());
            return stubFallbackEnabled ? stubEnrichment(content) : new AiNoteEnrichment("", List.of());
        }
    }

    private String callModel(String prompt) {
        String response = chatClient.prompt(prompt).call().content();
        return response == null ? "" : response;
    }

    private AiNoteEnrichment stubEnrichment(String content) {
        String collapsed = content == null ? "" : content.replaceAll("\\s+", " ").trim();
        String summary;
        if (collapsed.length() <= 200) {
            summary = collapsed;
        } else {
            summary = collapsed.substring(0, 200) + "...";
        }

        List<String> tags = extractKeywordTags(collapsed);
        return new AiNoteEnrichment(summary, tags);
    }

    private List<String> extractKeywordTags(String content) {
        Matcher matcher = WORD_PATTERN.matcher(content.toLowerCase(Locale.ROOT));
        LinkedHashSet<String> tags = new LinkedHashSet<>();

        while (matcher.find() && tags.size() < 5) {
            String word = matcher.group();
            if (word.length() < 4 || STOP_WORDS.contains(word)) {
                continue;
            }
            tags.add(word);
        }

        return tags.stream().toList();
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
                .limit(5)
                .toList();
    }

    public record AiNoteEnrichment(String summary, List<String> tagNames) {
    }
}
