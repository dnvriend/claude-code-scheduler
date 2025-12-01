# Plan: helm-chart-gen

## Summary

Create a Python CLI tool (`helm-chart-gen`) in `./helloworld-test` that generates complete Helm charts from YAML configuration files.

## Scope (from interview)

- **Components**: Full chart (Deployment, Service, ConfigMap, Secret, Ingress, HPA, PDB)
- **Input**: YAML config file
- **Output**: Complete Helm chart structure (ready for `helm install`)
- **Templating**: Pure Helm (Go templates), no validation

## Job Created

- **Job ID**: `6c21b385-da76-4a89-b552-aa7f10d82533`
- **Name**: `helm-chart-gen`
- **Tasks**: 10 atomic tasks

## Task Breakdown

| # | Task Name | Goal | Output |
|---|-----------|------|--------|
| 1 | `helmgen-project-setup` | Project scaffolding | pyproject.toml, Makefile, etc. |
| 2 | `helmgen-models-config` | Input config Pydantic models | models/config.py |
| 3 | `helmgen-models-chart` | Output chart Pydantic models | models/chart.py |
| 4 | `helmgen-templates-base` | Chart.yaml, values.yaml templates | templates/*.j2 |
| 5 | `helmgen-templates-deployment` | deployment.yaml template | templates/helm/deployment.yaml.j2 |
| 6 | `helmgen-templates-service` | service, configmap, secret templates | templates/helm/*.j2 |
| 7 | `helmgen-templates-advanced` | ingress, hpa, pdb templates | templates/helm/*.j2 |
| 8 | `helmgen-service-generator` | ChartGenerator service class | services/generator.py |
| 9 | `helmgen-cli-main` | CLI with generate command | cli.py |
| 10 | `helmgen-logging-completion` | Logging and shell completion | logging_config.py, completion.py |

## Execution Order

Tasks must be executed **sequentially** in order (1→10) due to dependencies.

## Next Steps

Run tasks via scheduler GUI or CLI:

```bash
# Run first task
claude-code-scheduler cli tasks run 2c8e2ecd-fe91-4929-b4ea-88db1be4dbee

# Or use /orchestrate with job.json
```

## Project Structure (Final)

```
helloworld-test/
├── helm_chart_gen/
│   ├── __init__.py
│   ├── _version.py
│   ├── cli.py
│   ├── completion.py
│   ├── logging_config.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   └── chart.py
│   ├── services/
│   │   ├── __init__.py
│   │   └── generator.py
│   └── templates/
│       ├── Chart.yaml.j2
│       ├── values.yaml.j2
│       └── helm/
│           ├── deployment.yaml.j2
│           ├── service.yaml.j2
│           ├── configmap.yaml.j2
│           ├── secret.yaml.j2
│           ├── ingress.yaml.j2
│           ├── hpa.yaml.j2
│           └── pdb.yaml.j2
├── tests/
├── pyproject.toml
├── Makefile
├── .mise.toml
└── README.md
```
