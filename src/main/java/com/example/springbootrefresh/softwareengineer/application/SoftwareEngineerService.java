package com.example.springbootrefresh.softwareengineer.application;

import com.example.springbootrefresh.softwareengineer.api.CreateSoftwareEngineerRequestDto;
import com.example.springbootrefresh.softwareengineer.api.SoftwareEngineerResponseDto;
import com.example.springbootrefresh.softwareengineer.domain.SoftwareEngineer;
import com.example.springbootrefresh.softwareengineer.domain.SoftwareEngineerNotFoundException;
import com.example.springbootrefresh.softwareengineer.persistence.SoftwareEngineerRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class SoftwareEngineerService {

    private static final Logger logger = LoggerFactory.getLogger(SoftwareEngineerService.class);

    private final SoftwareEngineerRepository softwareEngineerRepository;

    public SoftwareEngineerService(SoftwareEngineerRepository softwareEngineerRepository) {
        this.softwareEngineerRepository = softwareEngineerRepository;
    }

    public List<SoftwareEngineerResponseDto> getAllSoftwareEngineers() {
        List<SoftwareEngineerResponseDto> engineers = softwareEngineerRepository.findAll().stream()
                .map(this::toDto)
                .toList();
        logger.info("Retrieved {} software engineers", engineers.size());
        return engineers;
    }

    public SoftwareEngineerResponseDto addSoftwareEngineer(CreateSoftwareEngineerRequestDto request) {
        SoftwareEngineer softwareEngineer = new SoftwareEngineer(
                null,
                request.name(),
                request.techStack()
        );
        SoftwareEngineer savedEngineer = softwareEngineerRepository.save(softwareEngineer);
        logger.info("Created software engineer with id {}", savedEngineer.getId());
        return toDto(savedEngineer);
    }

    public SoftwareEngineerResponseDto getSoftwareEngineerById(Integer id) {
        logger.info("Retrieving software engineer with id {}", id);
        return toDto(findSoftwareEngineer(id));
    }

    public void deleteSoftwareEngineer(Integer id) {
        softwareEngineerRepository.delete(findSoftwareEngineer(id));
        logger.info("Deleted software engineer with id {}", id);
    }

    private SoftwareEngineer findSoftwareEngineer(Integer id) {
        return softwareEngineerRepository.findById(id).orElseThrow(
                () -> {
                    logger.warn("Software engineer with id {} was not found", id);
                    return new SoftwareEngineerNotFoundException(id);
                }
        );
    }

    private SoftwareEngineerResponseDto toDto(SoftwareEngineer softwareEngineer) {
        return new SoftwareEngineerResponseDto(
                softwareEngineer.getId(),
                softwareEngineer.getName(),
                softwareEngineer.getTechStack()
        );
    }
}
