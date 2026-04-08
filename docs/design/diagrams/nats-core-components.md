# C4 Level 3: nats-core Component Diagram

**Container:** nats-core (Python library)
**Date:** 2026-04-07

---

## Component Diagram

```mermaid
C4Component
    title Component Diagram for nats-core

    Container_Boundary(nats_core, "nats-core library") {
        Component(envelope, "envelope.py", "Pydantic", "MessageEnvelope base schema, EventType enum, payload_class_for_event_type() helper")
        Component(events, "events/", "Pydantic", "Typed payload schemas: pipeline, agent, jarvis, fleet")
        Component(manifest, "manifest.py", "Pydantic", "AgentManifest, IntentCapability, ToolCapability, ManifestRegistry ABC, InMemoryManifestRegistry")
        Component(topics, "topics.py", "Python", "Topic registry: typed constants, resolve(), for_project(), ALL_TOPICS")
        Component(client, "client.py", "nats-py", "NATSClient: typed pub/sub, fleet methods, call_agent_tool(), NATSKVManifestRegistry")
        Component(config, "config.py", "pydantic-settings", "NATSConfig: connection settings from env vars")
        Component(agent_config, "agent_config.py", "pydantic-settings", "AgentConfig, ModelConfig, GraphitiConfig: fleet-wide runtime config")
    }

    System_Ext(nats_server, "NATS Server", "JetStream broker + KV store")
    System_Ext(consumer, "Fleet Agents & Adapters", "All consuming services")
    System_Ext(mcp_adapter, "MCP Adapters", "Claude Desktop, MCP clients")

    Rel(consumer, envelope, "Import MessageEnvelope, EventType")
    Rel(consumer, events, "Import typed payload models")
    Rel(consumer, manifest, "Import AgentManifest, capabilities")
    Rel(consumer, topics, "Import topic constants, resolve()")
    Rel(consumer, client, "Use NATSClient for pub/sub")
    Rel(consumer, agent_config, "Import AgentConfig for runtime settings")
    Rel(mcp_adapter, manifest, "Derive MCP tools from ToolCapability")

    Rel(client, config, "Reads connection settings")
    Rel(client, topics, "Resolves topic strings")
    Rel(client, envelope, "Auto-wraps/unwraps MessageEnvelope")
    Rel(client, manifest, "Implements NATSKVManifestRegistry")
    Rel(client, nats_server, "Connects via nats-py")
    Rel(events, envelope, "Payloads carried in envelope")
    Rel(manifest, events, "IntentCapability used in fleet events")
    Rel(agent_config, config, "Nests NATSConfig")
```

---

## Dependency Chain

```
Config  ->  Client  ->  Topics  ->  Events  ->  Envelope
                |                      |
            AgentConfig            Manifest
```

- **Envelope** is the foundation -- no dependencies within the library
- **Events** depend on Envelope (payload schemas carried in envelope)
- **Manifest** depends on Events (IntentCapability used in fleet domain)
- **Topics** is standalone -- pure constants
- **Client** depends on Config, Topics, Envelope, Manifest
- **AgentConfig** depends on Config (nests NATSConfig)
- **Config** is standalone -- pure pydantic-settings

---

## Component Responsibilities

| Component | Internal Deps | External Deps | LOC (est.) |
|-----------|--------------|---------------|------------|
| `envelope.py` | None | pydantic | ~60 |
| `events/` | envelope | pydantic | ~200 |
| `manifest.py` | events | pydantic, abc | ~120 |
| `topics.py` | None | None | ~80 |
| `client.py` | config, topics, envelope, manifest | nats-py, pydantic | ~250 |
| `config.py` | None | pydantic-settings | ~30 |
| `agent_config.py` | config | pydantic, pydantic-settings | ~80 |
