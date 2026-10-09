package com.example.springbootrefresh.common.web;

import com.example.springbootrefresh.softwareengineer.domain.SoftwareEngineerNotFoundException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@RestControllerAdvice
public class ApiExceptionHandler {

    @ExceptionHandler(SoftwareEngineerNotFoundException.class)
    public ProblemDetail handleSoftwareEngineerNotFound(SoftwareEngineerNotFoundException exception) {
        return ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, exception.getMessage());
    }
}
