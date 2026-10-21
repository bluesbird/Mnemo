package com.mnemo.knowledgeservice.knowledgehub.application;

import com.openai.errors.RateLimitException;
import org.springframework.ai.chat.client.ChatClient;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.util.Locale;

@Service
public class NoteSummaryService {

    private static final Logger logger = LoggerFactory.getLogger(NoteSummaryService.class);

    private final ChatClient chatClient;
    private final boolean enabled;

    public NoteSummaryService(
            ChatClient.Builder chatClientBuilder,
            @Value("${app.summary.enabled:true}") boolean enabled
    ) {
        this.chatClient = chatClientBuilder.build();
        this.enabled = enabled;
    }

    public String summarizeNote(String title, String content) {
        if (!enabled) {
            throw new NoteSummaryException("Note summarization is disabled.");
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

            return toSummary(callModel(summaryPrompt));
        } catch (NoteSummaryException ex) {
            logger.warn("Note summarization failed: {}", ex.getMessage());
            throw ex;
        } catch (RateLimitException ex) {
            logger.warn("AI provider quota exceeded");
            throw new NoteSummaryException("AI provider quota exceeded. Please try again later.", ex);
        } catch (RuntimeException ex) {
            logger.warn("AI provider call failed ({})", ex.getClass().getSimpleName());
            throw new NoteSummaryException("Note summarization could not complete. Please try again.", ex);
        }
    }

    private String callModel(String prompt) {
        var response = chatClient.prompt(prompt).call().chatResponse();
        var result = response == null ? null : response.getResult();
        if (result == null) {
            throw new NoteSummaryException("Note summarization returned an empty answer. Please try again.");
        }
        String finishReason = result.getMetadata().getFinishReason();
        if ("length".equalsIgnoreCase(finishReason)) {
            throw new NoteSummaryException("Note summarization reached its token limit before finishing. Please try again.");
        }
        if (!"stop".equalsIgnoreCase(finishReason)) {
            throw new NoteSummaryException("Note summarization did not finish normally. Please try again.");
        }
        String content = result.getOutput().getText();
        if (content == null || content.isBlank()) {
            throw new NoteSummaryException("Note summarization returned an empty answer. Please try again.");
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
}
