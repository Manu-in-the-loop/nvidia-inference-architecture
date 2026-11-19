# Coding-agent inference

Private endpoint for Claude Code, OpenCode, Roo Code, and Cline on GLM-5.3 and Kimi K3. The racks are GB300 NVL72 and Vera Rubin NVL72. NVIDIA Dynamo serves the models.

## Read this first

- [Report](docs/architecture-report.md) covers the recommendation, the seat table, and the request path.
- [Assumptions you can change](docs/assumptions.md) lists every input, the current value, and which result moves when you edit it.

Seat counts are produced only by:

```bash
python3 capacity/model.py
```

Edit `capacity/scenarios.yaml` for usage, context, and cache policy. Edit `capacity/constants.json` for hardware and replica shape. Then rerun the command and refresh the table in the report from `capacity/results.md`.

## Diagrams

Open these HTML files in a browser:

- [Rack, network, and KV placement](diagrams/infrastructure.html)
- [Prompt path, hit and miss](diagrams/request-flow.html)
- [Weight sharding and the prompt path](diagrams/parallelism.html)

The JSON file next to each HTML page is the source for that diagram.
