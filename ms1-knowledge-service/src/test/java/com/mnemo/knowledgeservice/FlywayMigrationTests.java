package com.mnemo.knowledgeservice;

import org.flywaydb.core.Flyway;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.core.env.Environment;
import org.springframework.core.io.ClassPathResource;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.springframework.jdbc.datasource.init.ScriptUtils;
import org.springframework.orm.jpa.LocalContainerEntityManagerFactoryBean;
import org.springframework.orm.jpa.vendor.HibernateJpaVendorAdapter;

import javax.sql.DataSource;
import java.nio.file.Files;
import java.nio.file.Path;
import java.sql.Connection;
import java.sql.SQLException;
import java.util.Map;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

@SpringBootTest
class FlywayMigrationTests {

    @Autowired
    private Environment environment;

    @Test
    void freshSchemaMigratesValidatesAndCanBeStartedAgain() throws SQLException {
        String schema = createSchema();
        try {
            Flyway flyway = flywayFor(schema, false);

            assertEquals(1, flyway.migrate().migrationsExecuted);
            assertEquals(0, flyway.migrate().migrationsExecuted);
            assertEquals("SQL", historyType(schema));
            assertHibernateValidates(schema);
        } finally {
            dropSchema(schema);
        }
    }

    @Test
    void explicitlyBaselinedLegacySchemaKeepsItsDataAndRelationships() throws Exception {
        String schema = createSchema();
        try {
            try (Connection connection = schemaDataSource().getConnection()) {
                connection.setSchema(schema);
                ScriptUtils.executeSqlScript(connection, new ClassPathResource("db/legacy-schema.sql"));
                executePreflight(connection);
            }

            Flyway flyway = flywayFor(schema, true);
            assertEquals(0, flyway.migrate().migrationsExecuted);
            assertEquals("BASELINE", historyType(schema));
            assertEquals(1, scalar("SELECT count(*) FROM " + schema + ".note "
                    + "WHERE title = 'Legacy note' AND content = 'Keep this content' "
                    + "AND summary = 'Keep this summary' AND source_hash = 'legacy-hash'"));
            assertEquals(1, scalar("SELECT count(*) FROM " + schema + ".note_tags nt "
                    + "JOIN " + schema + ".note n ON n.id = nt.note_id "
                    + "JOIN " + schema + ".tag t ON t.id = nt.tag_id "
                    + "WHERE n.title = 'Legacy note' AND t.name = 'legacy-phase11'"));
            assertEquals(0, flyway.migrate().migrationsExecuted);
            assertHibernateValidates(schema);
        } finally {
            dropSchema(schema);
        }
    }

    @Test
    void legacyPreflightRejectsAnUnrecognizedSchema() throws Exception {
        String schema = createSchema();
        try {
            try (Connection connection = schemaDataSource().getConnection();
                 var statement = connection.createStatement()) {
                connection.setSchema(schema);
                statement.execute("CREATE TABLE unrelated_table (id BIGINT PRIMARY KEY)");
                assertThrows(SQLException.class, () -> executePreflight(connection));
            }
        } finally {
            dropSchema(schema);
        }
    }

    private void executePreflight(Connection connection) throws Exception {
        try (var statement = connection.createStatement()) {
            statement.execute(Files.readString(Path.of("docs/legacy-schema-preflight.sql")));
        }
    }

    private Flyway flywayFor(String schema, boolean baselineOnMigrate) {
        return Flyway.configure()
                .dataSource(schemaDataSource())
                .locations("classpath:db/migration")
                .schemas(schema)
                .defaultSchema(schema)
                .baselineOnMigrate(baselineOnMigrate)
                .baselineVersion("1")
                .load();
    }

    private String createSchema() throws SQLException {
        String schema = "phase11_" + UUID.randomUUID().toString().replace("-", "");
        try (Connection connection = schemaDataSource().getConnection();
             var statement = connection.createStatement()) {
            statement.execute("CREATE SCHEMA " + schema);
        }
        return schema;
    }

    private void dropSchema(String schema) throws SQLException {
        try (Connection connection = schemaDataSource().getConnection();
             var statement = connection.createStatement()) {
            statement.execute("DROP SCHEMA " + schema + " CASCADE");
        }
    }

    private String historyType(String schema) throws SQLException {
        try (Connection connection = schemaDataSource().getConnection();
             var statement = connection.createStatement();
             var result = statement.executeQuery(
                     "SELECT type FROM " + schema + ".flyway_schema_history ORDER BY installed_rank LIMIT 1")) {
            if (!result.next()) {
                throw new AssertionError("Flyway schema history has no applied version");
            }
            return result.getString(1);
        }
    }

    private int scalar(String sql) throws SQLException {
        try (Connection connection = schemaDataSource().getConnection();
             var statement = connection.createStatement();
             var result = statement.executeQuery(sql)) {
            if (!result.next()) {
                throw new AssertionError("Query returned no rows: " + sql);
            }
            return result.getInt(1);
        }
    }

    private void assertHibernateValidates(String schema) {
        var validator = new LocalContainerEntityManagerFactoryBean();
        validator.setDataSource(schemaDataSource());
        validator.setPackagesToScan("com.mnemo.knowledgeservice.knowledgehub.domain");
        validator.setJpaVendorAdapter(new HibernateJpaVendorAdapter());
        validator.setJpaPropertyMap(Map.of(
                "hibernate.hbm2ddl.auto", "validate",
                "hibernate.default_schema", schema,
                "hibernate.physical_naming_strategy",
                "org.hibernate.boot.model.naming.CamelCaseToUnderscoresNamingStrategy"
        ));
        try {
            validator.afterPropertiesSet();
        } finally {
            validator.destroy();
        }
    }

    private DataSource schemaDataSource() {
        var source = new DriverManagerDataSource();
        source.setDriverClassName(environment.getRequiredProperty("spring.datasource.driver-class-name"));
        source.setUrl(environment.getRequiredProperty("spring.datasource.url"));
        source.setUsername(environment.getRequiredProperty("spring.datasource.username"));
        source.setPassword(environment.getRequiredProperty("spring.datasource.password"));
        return source;
    }
}
