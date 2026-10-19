package com.mnemo.knowledgeservice;

import com.mnemo.knowledgeservice.knowledgehub.application.AiEnrichmentException;
import com.mnemo.knowledgeservice.knowledgehub.application.OllamaAiService;
import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.Test;
import org.springframework.ai.chat.client.ChatClient;
import org.springframework.ai.chat.model.ChatModel;
import org.springframework.ai.model.ollama.autoconfigure.OllamaApiAutoConfiguration;
import org.springframework.ai.model.ollama.autoconfigure.OllamaChatAutoConfiguration;
import org.springframework.ai.model.openai.autoconfigure.OpenAiChatAutoConfiguration;
import org.springframework.ai.model.openai.autoconfigure.OpenAiAudioSpeechAutoConfiguration;
import org.springframework.ai.model.openai.autoconfigure.OpenAiAudioTranscriptionAutoConfiguration;
import org.springframework.ai.model.openai.autoconfigure.OpenAiEmbeddingAutoConfiguration;
import org.springframework.ai.model.openai.autoconfigure.OpenAiImageAutoConfiguration;
import org.springframework.ai.model.openai.autoconfigure.OpenAiModerationAutoConfiguration;
import org.springframework.ai.model.tool.autoconfigure.ToolCallingAutoConfiguration;
import org.springframework.ai.ollama.OllamaChatModel;
import org.springframework.ai.openai.OpenAiChatModel;
import org.springframework.boot.autoconfigure.AutoConfigurations;
import org.springframework.boot.test.context.runner.ApplicationContextRunner;
import org.springframework.core.io.support.ResourcePropertySource;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.junit.jupiter.api.Assertions.assertThrows;

class AiProviderConfigurationTests {

    private ApplicationContextRunner context(boolean groq) {
        return new ApplicationContextRunner()
                .withInitializer(context -> {
                    try {
                        var sources = context.getEnvironment().getPropertySources();
                        if (groq) {
                            sources.addLast(new ResourcePropertySource("classpath:application-groq.properties"));
                        }
                        sources.addLast(new ResourcePropertySource("classpath:application.properties"));
                    } catch (java.io.IOException ex) {
                        throw new IllegalStateException(ex);
                    }
                })
                .withConfiguration(AutoConfigurations.of(
                        OllamaApiAutoConfiguration.class, OllamaChatAutoConfiguration.class,
                        OpenAiChatAutoConfiguration.class, ToolCallingAutoConfiguration.class,
                        OpenAiAudioSpeechAutoConfiguration.class,
                        OpenAiAudioTranscriptionAutoConfiguration.class,
                        OpenAiEmbeddingAutoConfiguration.class, OpenAiImageAutoConfiguration.class,
                        OpenAiModerationAutoConfiguration.class
                ));
    }

    @Test
    void localDefaultsSelectOllamaWithoutAGroqKey() {
        context(false).run(context -> {
            assertThat(context).hasNotFailed().hasSingleBean(ChatModel.class);
            assertThat(context.getBean(ChatModel.class)).isInstanceOf(OllamaChatModel.class);
            assertThat(context).doesNotHaveBean(OpenAiChatModel.class);
        });
    }

    @Test
    void groqProfileUsesCompatibleRequestAndValidatesResponses() throws Exception {
        var requests = new ArrayList<JsonNode>();
        var authorizations = new ArrayList<String>();
        var mapper = new ObjectMapper();
        var server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/openai/v1/chat/completions", exchange -> {
            requests.add(mapper.readTree(exchange.getRequestBody().readAllBytes()));
            authorizations.add(exchange.getRequestHeaders().getFirst("Authorization"));
            int call = requests.size();
            if (call == 4) {
                byte[] error = """
                        {"error":{"message":"Test quota exceeded","type":"rate_limit_error","code":"rate_limit_exceeded"}}
                        """.getBytes(StandardCharsets.UTF_8);
                exchange.getResponseHeaders().add("Content-Type", "application/json");
                exchange.sendResponseHeaders(429, error.length);
                exchange.getResponseBody().write(error);
                exchange.close();
                return;
            }
            String finishReason = call == 3 ? "length" : "stop";
            String content = call == 1 ? "This note describes a cactus." : "gardening, cactus";
            byte[] response = ("""
                    {"id":"test-completion","object":"chat.completion","created":1,
                     "model":"qwen/qwen3.8-27b",
                     "choices":[{"index":0,"finish_reason":"%s",
                       "message":{"role":"assistant","content":"%s"}}],
                     "usage":{"prompt_tokens":10,"completion_tokens":8,"total_tokens":18}}
                    """.formatted(finishReason, content)).getBytes(StandardCharsets.UTF_8);
            exchange.getResponseHeaders().add("Content-Type", "application/json");
            exchange.sendResponseHeaders(200, response.length);
            exchange.getResponseBody().write(response);
            exchange.close();
        });
        server.start();
        try {
            context(true).withPropertyValues(
                    "GROQ_API_KEY=test-key-not-a-real-secret",
                    "spring.ai.openai.base-url=http://127.0.0.1:" + server.getAddress().getPort() + "/openai/v1"
            ).run(context -> {
                assertThat(context).hasNotFailed().hasSingleBean(ChatModel.class);
                assertThat(context.getEnvironment().getProperty("spring.ai.openai.base-url"))
                        .isEqualTo("http://127.0.0.1:" + server.getAddress().getPort() + "/openai/v1");
                var model = context.getBean(ChatModel.class);
                assertThat(model).isInstanceOf(OpenAiChatModel.class);
                assertThat(context).doesNotHaveBean(OllamaChatModel.class);
                var service = new OllamaAiService(ChatClient.builder(model), true);
                var result = service.enrichNote("Cactus", "A cactus wears a hat.");
                assertThat(result.summary()).isEqualTo("This note describes a cactus.");
                assertThat(result.tagNames()).isEqualTo(List.of("gardening", "cactus"));
                assertThrows(AiEnrichmentException.class,
                        () -> service.enrichNote("Cactus", "A cactus wears a hat."));
                assertThat(requests).hasSize(3);
                var quotaError = assertThrows(AiEnrichmentException.class,
                        () -> service.enrichNote("Cactus", "A cactus wears a hat."));
                assertThat(quotaError.getMessage()).contains("quota exceeded");
                assertThat(requests).hasSize(4);
                for (var request : requests) {
                    assertThat(request.path("model").asText()).isEqualTo("qwen/qwen3.8-27b");
                    assertThat(request.path("max_completion_tokens").asInt()).isEqualTo(2048);
                    assertThat(request.path("reasoning_effort").asText()).isEqualTo("none");
                }
                assertThat(authorizations).containsOnly("Bearer test-key-not-a-real-secret");
            });
        } finally {
            server.stop(0);
        }
    }
}
