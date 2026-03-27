# Dev Manager Flow

```mermaid
graph TD
    classDef intake fill:#fcd34d,stroke:#b45309,color:#000
    classDef process fill:#60a5fa,stroke:#1e3a8a,color:#fff
    classDef object fill:#1f2937,stroke:#9ca3af,color:#fff
    classDef route fill:#10b981,stroke:#064e3b,color:#fff

    Start([Incoming Feature/Bug Request])::intake
    Log[Log Request to Backoffice]::process
    Requests[(Requests)]::object
    Match[Match against Project Map]::process
    Assign[Create Actionable Assignment]::process
    Assignments[(Assignments)]::object

    RouteDesign{Requires Design?}::route
    RouteCoder{Requires Coding?}::route
    RouteQA{Requires Testing?}::route

    SendDesign[Dispatch to Solace Design]::process
    SendCoder[Dispatch to Solace Coder]::process
    SendQA[Dispatch to Solace QA]::process

    Start --> Log
    Log --> Requests
    Requests --> Match
    Match --> Assign
    Assign --> Assignments

    Assignments --> RouteDesign
    RouteDesign -- Yes --> SendDesign
    RouteDesign -- No --> RouteCoder

    SendDesign --> RouteCoder
    RouteCoder -- Yes --> SendCoder
    RouteCoder -- No --> RouteQA

    SendCoder --> RouteQA
    RouteQA -- Yes --> SendQA
    RouteQA -- No --> End([Release Ready])

    SendQA --> End
```
