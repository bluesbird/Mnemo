package com.example.springbootrefresh.softwareengineer.api;

import java.util.List;

public record SoftwareEngineerResponseDto(Integer id, String name, List<String> techStack) {
}
