package com.personalknowledgehub.knowledgeservice.knowledgehub.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.JoinTable;
import jakarta.persistence.ManyToMany;
import jakarta.persistence.Table;
import jakarta.validation.constraints.NotBlank;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.LocalDateTime;
import java.util.HashSet;
import java.util.Objects;
import java.util.Set;

@Entity
@Table(name = "note")
@Getter
@NoArgsConstructor
public class Note {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @NotBlank(message = "Title cannot be blank")
    private String title;

    @NotBlank(message = "Content cannot be blank")
    @Column(columnDefinition = "TEXT")
    private String content;

    @Column(columnDefinition = "TEXT")
    private String summary;

    @Column(nullable = false, length = 64, columnDefinition = "varchar(64) default ''")
    private String sourceHash;

    @ManyToMany
    @JoinTable(
            name = "note_tags",
            joinColumns = @JoinColumn(name = "note_id"),
            inverseJoinColumns = @JoinColumn(name = "tag_id")
    )
    private Set<Tag> tags = new HashSet<>();

    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;

    public Note(String title, String content) {
        final LocalDateTime now = LocalDateTime.now();

        this.title = title;
        this.content = content;
        this.summary = null;
        this.createdAt = now;
        this.updatedAt = now;
        this.sourceHash = computeSourceHash(title, content);
    }

    public void setTitle(String title) {
        this.title = title;
    }

    public void setContent(String content) {
        this.content = content;
    }

    public void setSummary(String summary) {
        this.summary = summary;
    }

    public void setTags(Set<Tag> tags) {
        this.tags = tags;
    }

    public void setUpdatedAt(LocalDateTime updatedAt) {
        this.updatedAt = updatedAt;
    }

    public void updateCoreContent(String title, String content) {
        this.title = title;
        this.content = content;
        this.sourceHash = computeSourceHash(title, content);
    }

    public boolean initializeIndexMetadataIfMissing() {
        if (this.sourceHash != null && !this.sourceHash.isBlank()) {
            return false;
        }
        this.sourceHash = computeSourceHash(this.title, this.content);
        return true;
    }

    private static String computeSourceHash(String title, String content) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            digest.update("v1\0".getBytes(StandardCharsets.UTF_8));
            digest.update(safeValue(title).getBytes(StandardCharsets.UTF_8));
            digest.update("\0".getBytes(StandardCharsets.UTF_8));
            digest.update(safeValue(content).getBytes(StandardCharsets.UTF_8));
            byte[] hashBytes = digest.digest();
            StringBuilder hex = new StringBuilder(hashBytes.length * 2);
            for (byte hashByte : hashBytes) {
                hex.append(String.format("%02x", hashByte));
            }
            return hex.toString();
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException("SHA-256 is not available", e);
        }
    }

    private static String safeValue(String value) {
        return value == null ? "" : value;
    }

    @Override
    public boolean equals(Object o) {
        if (o == null || getClass() != o.getClass()) return false;
        Note note = (Note) o;
        return Objects.equals(id, note.id);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id);
    }
}
