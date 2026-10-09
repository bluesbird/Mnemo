package com.example.springbootrefresh.softwareengineer;

public class SoftwareEngineerNotFoundException extends RuntimeException {

    public SoftwareEngineerNotFoundException(Integer id) {
        super("Software Engineer with id " + id + " does not exist");
    }
}
