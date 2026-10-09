package com.example.springbootrefresh;

public class SoftwareEngineerNotFoundException extends RuntimeException {

    public SoftwareEngineerNotFoundException(Integer id) {
        super("Software Engineer with id " + id + " does not exist");
    }
}
