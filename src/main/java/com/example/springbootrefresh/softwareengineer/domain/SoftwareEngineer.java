package com.example.springbootrefresh.softwareengineer.domain;

import jakarta.persistence.CollectionTable;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.ElementCollection;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.OrderColumn;

import java.util.ArrayList;
import java.util.List;
import java.util.Objects;

@Entity
public class SoftwareEngineer {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Integer id;
    private String name;
    @ElementCollection
    @CollectionTable(
            name = "software_engineer_tech_stack",
            joinColumns = @JoinColumn(name = "software_engineer_id")
    )
    @OrderColumn(name = "position")
    @Column(name = "technology", nullable = false)
    private List<String> techStack = new ArrayList<>();

    public SoftwareEngineer() {
    }

    public SoftwareEngineer(Integer id, String name, List<String> techStack) {
        this.id = id;
        this.name = name;
        this.techStack = new ArrayList<>(techStack);
    }

    public Integer getId() {
        return id;
    }

    public void setId(Integer id) {
        this.id = id;
    }

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public List<String> getTechStack() {
        return techStack;
    }

    public void setTechStack(List<String> techStack) {
        this.techStack = new ArrayList<>(techStack);
    }

    @Override
    public boolean equals(Object o) {
        if (o == null || getClass() != o.getClass()) return false;
        SoftwareEngineer that = (SoftwareEngineer) o;
        return Objects.equals(id, that.id) && Objects.equals(name, that.name) && Objects.equals(techStack, that.techStack);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, name, techStack);
    }
}
