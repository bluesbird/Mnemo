package com.personalknowledgehub.knowledgeservice.knowledgehub.persistence;

import com.personalknowledgehub.knowledgeservice.knowledgehub.domain.Tag;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.Optional;

public interface TagRepository extends JpaRepository<Tag, Long> {
    Optional<Tag> findByName(String name);
}
