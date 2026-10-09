package com.example.springbootrefresh.softwareengineer.application;

import com.example.springbootrefresh.softwareengineer.api.CreateSoftwareEngineerRequestDto;
import com.example.springbootrefresh.softwareengineer.api.SoftwareEngineerResponseDto;
import com.example.springbootrefresh.softwareengineer.domain.SoftwareEngineer;
import com.example.springbootrefresh.softwareengineer.domain.SoftwareEngineerNotFoundException;
import com.example.springbootrefresh.softwareengineer.persistence.SoftwareEngineerRepository;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class SoftwareEngineerService {

    private final SoftwareEngineerRepository softwareEngineerRepository;

    public SoftwareEngineerService(SoftwareEngineerRepository softwareEngineerRepository) {
        this.softwareEngineerRepository = softwareEngineerRepository;
    }

    public List<SoftwareEngineerResponseDto> getAllSoftwareEngineers() {
        return softwareEngineerRepository.findAll().stream()
                .map(this::toDto)
                .toList();
    }

    public SoftwareEngineerResponseDto addSoftwareEngineer(CreateSoftwareEngineerRequestDto request) {
        SoftwareEngineer softwareEngineer = new SoftwareEngineer(
                null,
                request.name(),
                request.techStack()
        );
        return toDto(softwareEngineerRepository.save(softwareEngineer));
    }

    public SoftwareEngineerResponseDto getSoftwareEngineerById(Integer id) {
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

    private SoftwareEngineerResponseDto toDto(SoftwareEngineer softwareEngineer) {
        return new SoftwareEngineerResponseDto(
                softwareEngineer.getId(),
                softwareEngineer.getName(),
                softwareEngineer.getTechStack()
        );
    }
}
