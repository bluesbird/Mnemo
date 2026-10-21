package com.mnemo.knowledgeservice.knowledgehub.application;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.Resource;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.util.List;

@Component
public class StarterNoteCatalog {

    private final List<StarterNote> notes;

    public StarterNoteCatalog(@Value("classpath:starter-notes.json") Resource starterNotes) {
        try (var input = starterNotes.getInputStream()) {
            this.notes = List.copyOf(
                    new ObjectMapper().readValue(input, new TypeReference<>() {})
            );
        } catch (IOException e) {
            throw new IllegalStateException("Could not load starter notes", e);
        }
        if (notes.isEmpty()) {
            throw new IllegalStateException("Starter note catalog cannot be empty");
        }
    }

    public List<StarterNote> notes() {
        return notes;
    }

    public record StarterNote(String title, String content) {
    }
}
