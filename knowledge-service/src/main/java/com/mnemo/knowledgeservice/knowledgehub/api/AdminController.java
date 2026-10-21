package com.mnemo.knowledgeservice.knowledgehub.api;

import com.mnemo.knowledgeservice.knowledgehub.api.dto.DatabaseResetResponseDto;
import com.mnemo.knowledgeservice.knowledgehub.application.DatabaseResetService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;

@RestController
@RequestMapping("api/v1/admin")
@Tag(name = "Administration", description = "Authenticated administrative operations")
public class AdminController {

    private final DatabaseResetService databaseResetService;
    private final String resetApiKey;

    public AdminController(
            DatabaseResetService databaseResetService,
            @Value("${app.reset.api-key:}") String resetApiKey
    ) {
        this.databaseResetService = databaseResetService;
        this.resetApiKey = resetApiKey;
    }

    @PostMapping("/reset-database")
    @Operation(summary = "Reset notes to starter data and queue an RAG service full index rebuild")
    public ResponseEntity<DatabaseResetResponseDto> resetDatabase(
            @RequestHeader(value = "X-Mnemo-Reset-Key", required = false) String presentedKey
    ) {
        if (resetApiKey.isBlank()) {
            throw new ResponseStatusException(
                    HttpStatus.SERVICE_UNAVAILABLE,
                    "Database reset is disabled because no reset key is configured."
            );
        }
        if (!matchesResetKey(presentedKey)) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Invalid reset key.");
        }

        int restoredNoteCount = databaseResetService.reset();
        return ResponseEntity.accepted().body(
                new DatabaseResetResponseDto("reset", restoredNoteCount, "queued")
        );
    }

    private boolean matchesResetKey(String presentedKey) {
        if (presentedKey == null) {
            return false;
        }
        return MessageDigest.isEqual(
                resetApiKey.getBytes(StandardCharsets.UTF_8),
                presentedKey.getBytes(StandardCharsets.UTF_8)
        );
    }
}
