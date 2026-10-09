package com.example.springbootrefresh;

import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

import java.util.List;

@Service
public class SoftwareEngineerService {

    private final SoftwareEngineerRepository softwareEngineerRepository;

    public SoftwareEngineerService(SoftwareEngineerRepository softwareEngineerRepository) {
        this.softwareEngineerRepository = softwareEngineerRepository;
    }

    public List<SoftwareEngineerDto> getAllSoftwareEngineers() {
        return softwareEngineerRepository.findAll().stream()
                .map(this::toDto)
                .toList();
    }

    public SoftwareEngineerDto addSoftwareEngineer(SoftwareEngineerDto softwareEngineerDto) {
        SoftwareEngineer softwareEngineer = new SoftwareEngineer(
                null,
                softwareEngineerDto.name(),
                softwareEngineerDto.techStack()
        );
        return toDto(softwareEngineerRepository.save(softwareEngineer));
    }

    public SoftwareEngineerDto getSoftwareEngineerById(Integer id) {
        SoftwareEngineer softwareEngineer = softwareEngineerRepository.findById(id).orElseThrow(
                () -> new ResponseStatusException(
                        HttpStatus.NOT_FOUND,
                        "Software Engineer with id " + id + " does not exist"
                )
        );
        return toDto(softwareEngineer);
    }

    private SoftwareEngineerDto toDto(SoftwareEngineer softwareEngineer) {
        return new SoftwareEngineerDto(
                softwareEngineer.getId(),
                softwareEngineer.getName(),
                softwareEngineer.getTechStack()
        );
    }
}
