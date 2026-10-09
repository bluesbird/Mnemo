package com.example.springbootrefresh.softwareengineer.api;

import java.util.List;

public record CreateSoftwareEngineerRequestDto(String name, List<String> techStack) {
}
