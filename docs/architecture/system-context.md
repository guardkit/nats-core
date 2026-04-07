# C4 System Context -- nats-core

## System Context Diagram

```mermaid
C4Context
    title nats-core System Context

    Person(agent_dev, "Agent Developer", "Builds agents and services for the fleet")
    Person(adapter_dev, "Adapter Developer", "Builds Telegram, Reachy, CLI adapters")

    System(nats_core, "nats-core", "Shared contract library: message schemas, topic registry, typed NATS client")

    System_Ext(jarvis, "Jarvis Router", "Intent classification and agent dispatch")
    System_Ext(po_agent, "Product Owner Agent", "Feature ideation and planning")
    System_Ext(architect, "Architect Agent", "System design and ADRs")
    System_Ext(guardkit, "GuardKit Factory", "Automated build pipeline")
    System_Ext(telegram, "Telegram Adapter", "Chat interface to Jarvis")
    System_Ext(reachy, "Reachy Bridge", "Robot voice interface")
    System_Ext(nats_server, "NATS Server", "JetStream message broker + KV store")

    Rel(agent_dev, nats_core, "pip install, import")
    Rel(adapter_dev, nats_core, "pip install, import")
    Rel(jarvis, nats_core, "Imports schemas, uses NATSClient")
    Rel(po_agent, nats_core, "Imports event schemas")
    Rel(architect, nats_core, "Imports event schemas")
    Rel(guardkit, nats_core, "Imports pipeline events, publishes build status")
    Rel(telegram, nats_core, "Imports Jarvis events")
    Rel(reachy, nats_core, "Imports Jarvis events")
    Rel(nats_core, nats_server, "NATSClient connects via nats-py")
```

_All fleet consumers depend on nats-core for schemas and typed pub/sub. The single outbound dependency is the NATS server, accessed via the NATSClient module._
