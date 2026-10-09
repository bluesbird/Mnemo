package com.example.springbootrefresh.softwareengineer.persistence;

import com.example.springbootrefresh.softwareengineer.domain.SoftwareEngineer;
import org.springframework.data.jpa.repository.JpaRepository;

public interface SoftwareEngineerRepository extends JpaRepository<SoftwareEngineer,Integer> {
}
