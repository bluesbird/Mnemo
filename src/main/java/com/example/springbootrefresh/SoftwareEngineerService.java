package com.example.springbootrefresh;

import org.springframework.stereotype.Service;

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

    public void addSoftwareEngineer(SoftwareEngineerDto softwareEngineerDto) {
        SoftwareEngineer softwareEngineer = new SoftwareEngineer(
                null,
                softwareEngineerDto.name(),
                softwareEngineerDto.techStack()
        );
        softwareEngineerRepository.save(softwareEngineer);
    }

    public SoftwareEngineerDto getSoftwareEngineerById(Integer id) {
        SoftwareEngineer softwareEngineer = softwareEngineerRepository.findById(id).orElseThrow(
                () -> new IllegalStateException("Software Engineer with id " + id + " does not exist")
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
