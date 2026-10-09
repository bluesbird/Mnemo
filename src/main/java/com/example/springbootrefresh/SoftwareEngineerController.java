package com.example.springbootrefresh;

import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("api/v1/software-engineers")
public class SoftwareEngineerController {

    private final SoftwareEngineerService softwareEngineerService;

    public SoftwareEngineerController(SoftwareEngineerService softwareEngineerService) {
        this.softwareEngineerService = softwareEngineerService;
    }

    @GetMapping
    public List<SoftwareEngineer> getAllEngineers() {
        return softwareEngineerService.getAllSoftwareEngineers();
    }

    @GetMapping("/{id}")
    public SoftwareEngineer getEngineerById(@PathVariable Integer id) { // TODO: @PathVariable vs @RequestParam?
        return softwareEngineerService.getSoftwareEngineerById(id);
    }

    @PostMapping
    public void addSoftwareEngineer(@RequestBody SoftwareEngineer softwareEngineer) {
        softwareEngineerService.addSoftwareEngineer(softwareEngineer);
    }
}
