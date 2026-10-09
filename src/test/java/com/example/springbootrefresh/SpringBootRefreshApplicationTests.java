package com.example.springbootrefresh;

import com.example.springbootrefresh.softwareengineer.domain.SoftwareEngineer;
import com.example.springbootrefresh.softwareengineer.persistence.SoftwareEngineerRepository;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.transaction.annotation.Transactional;

import jakarta.persistence.EntityManager;
import jakarta.persistence.PersistenceContext;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;

@SpringBootTest
class SpringBootRefreshApplicationTests {

    @Autowired
    private SoftwareEngineerRepository softwareEngineerRepository;

    @PersistenceContext
    private EntityManager entityManager;

    @Test
    void contextLoads() {
    }

    @Test
    @Transactional
    void persistsTechStackAsAnOrderedList() {
        SoftwareEngineer saved = softwareEngineerRepository.save(
                new SoftwareEngineer(null, "Test Engineer", List.of("Java", "Spring"))
        );

        entityManager.flush();
        entityManager.clear();

        SoftwareEngineer loaded = softwareEngineerRepository.findById(saved.getId()).orElseThrow();
        assertEquals(List.of("Java", "Spring"), loaded.getTechStack());
    }
}
