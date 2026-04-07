# C4 Container Diagram -- nats-core

## Container Diagram

```mermaid
C4Container
    title Container Diagram for nats-core

    Container_Boundary(nats_core, "nats-core (Python library)") {
        Container(envelope, "envelope.py", "Pydantic", "MessageEnvelope base schema -- wire format for all messages")
        Container(events, "events/", "Pydantic", "Typed payload schemas: pipeline, agent, jarvis, fleet")
        Container(manifest, "manifest.py", "Pydantic", "AgentManifest, IntentCapability, ToolCapability")
        Container(topics, "topics.py", "Python", "Topic registry -- typed constants, resolution, project scoping")
        Container(client, "client.py", "nats-py", "NATSClient -- typed publish/subscribe, fleet convenience methods")
        Container(config, "config.py", "pydantic-settings", "NATSConfig -- connection settings from environment")
    }

    System_Ext(nats_server, "NATS Server", "JetStream broker + KV store")
    System_Ext(consumer, "Fleet Agents & Adapters", "All consuming services")

    Rel(consumer, envelope, "Import MessageEnvelope")
    Rel(consumer, events, "Import event payload models")
    Rel(consumer, manifest, "Import AgentManifest")
    Rel(consumer, topics, "Import topic constants")
    Rel(consumer, client, "Use NATSClient for pub/sub")

    Rel(client, config, "Reads connection settings")
    Rel(client, topics, "Resolves topic strings")
    Rel(client, envelope, "Wraps/unwraps messages")
    Rel(client, nats_server, "Connects via nats-py")
    Rel(events, envelope, "Payloads carried in envelope")
    Rel(manifest, events, "IntentCapability used in fleet events")
```

_Dependency flow: Client -> Topics -> Events -> Envelope, with Config feeding Client only. All consumer imports flow into the library boundary._
