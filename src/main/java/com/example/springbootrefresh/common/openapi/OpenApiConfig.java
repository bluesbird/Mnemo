package com.example.springbootrefresh.common.openapi;

import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Contact;
import io.swagger.v3.oas.models.info.Info;
import io.swagger.v3.oas.models.servers.Server;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.util.List;

@Configuration
public class OpenApiConfig {

    @Bean
    public OpenAPI knowledgeHubOpenApi() {
        return new OpenAPI()
                .info(new Info()
                        .title("Personal Knowledge Hub API")
                        .description("API for managing notes and AI enrichment.")
                        .version("v1")
                        .contact(new Contact().name("Lorenz")))
                .servers(List.of(new Server().url("http://localhost:8080").description("Local")));
    }
}
