## ADDED Requirements

### Requirement: STT providers shall use a shared configuration contract
The system SHALL configure STT providers through a shared provider contract rather than hard-coding a single local service.

#### Scenario: Local provider is selected
- **WHEN** the project is configured to use a local STT provider such as `speaches`
- **THEN** the system MUST resolve the provider through shared fields including provider name, base URL, model, timeout, and optional API key

#### Scenario: Cloud provider is selected
- **WHEN** the project is configured to use a cloud STT provider such as OpenAI or Groq
- **THEN** the system MUST use the same shared configuration contract so the runtime can switch providers without changing collection logic

### Requirement: The repository shall include a standard local STT deployment asset
The system SHALL provide a versioned local deployment entrypoint for the default STT service used by the project.

#### Scenario: Operator needs the default local STT deployment
- **WHEN** a user or Agent chooses the local provider path
- **THEN** the repository MUST provide deployment assets under `infra/stt/speaches`

#### Scenario: Local deployment is used for repeated setup
- **WHEN** the local provider is deployed multiple times across environments
- **THEN** the deployment assets MUST remain repository-controlled so Agents can reference a stable path during setup and troubleshooting

### Requirement: Pre-flight checks shall validate STT provider availability
The system SHALL extend pre-required checks to validate the currently selected STT provider before the fallback flow depends on it.

#### Scenario: Local STT provider is not healthy
- **WHEN** pre-flight checks detect that the configured local STT service is not reachable or healthy
- **THEN** the Agent MUST stop the dependent workflow and assist the user in starting or repairing the service before continuing

#### Scenario: Cloud STT provider is selected
- **WHEN** pre-flight checks run for a cloud provider configuration
- **THEN** the system MUST validate the required provider settings such as base URL, model, and API key before declaring the environment ready

### Requirement: Agent setup flow shall ask for deployment mode when configuration is incomplete
The system SHALL require an explicit local-versus-cloud decision before trying to auto-repair a missing STT setup.

#### Scenario: STT provider is not yet configured
- **WHEN** the Agent detects that STT fallback is needed but no valid provider configuration is available
- **THEN** the Agent MUST ask whether the user wants to use a local deployment or a cloud service before applying setup steps
