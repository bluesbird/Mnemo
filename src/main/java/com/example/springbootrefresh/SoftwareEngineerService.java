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

    public SoftwareEngineerDto addSoftwareEngineer(SoftwareEngineerDto softwareEngineerDto) {
        SoftwareEngineer softwareEngineer = new SoftwareEngineer(
                null,
                softwareEngineerDto.name(),
                softwareEngineerDto.techStack()
        );
        return toDto(softwareEngineerRepository.save(softwareEngineer));
    }

    public SoftwareEngineerDto getSoftwareEngineerById(Integer id) {
        return toDto(findSoftwareEngineer(id));
    }

    public void deleteSoftwareEngineer(Integer id) {
        softwareEngineerRepository.delete(findSoftwareEngineer(id));
    }

    private SoftwareEngineer findSoftwareEngineer(Integer id) {
        return softwareEngineerRepository.findById(id).orElseThrow(
                () -> new SoftwareEngineerNotFoundException(id)
        );
    }

    private SoftwareEngineerDto toDto(SoftwareEngineer softwareEngineer) {
        return new SoftwareEngineerDto(
                softwareEngineer.getId(),
                softwareEngineer.getName(),
                softwareEngineer.getTechStack()
        );
    }
}
