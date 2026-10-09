package com.example.springbootrefresh;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@SpringBootApplication
@RestController
public class SpringBootRefreshApplication {

    public static void main(String[] args) {
        SpringApplication.run(SpringBootRefreshApplication.class, args);
    }

    @GetMapping
    public String helloWorld() {
        return "Hello World!";
    }

}
