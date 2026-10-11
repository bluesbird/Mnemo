package com.example.springbootrefresh.knowledgehub.persistence;

import com.example.springbootrefresh.knowledgehub.domain.Tag;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.Optional;

public interface TagRepository extends JpaRepository<Tag, Long> {
    Optional<Tag> findByName(String name);
}
