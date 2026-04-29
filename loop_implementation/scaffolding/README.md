# Loop monorepo — scaffolding

Drop these files into a fresh repo (`loop-ai/loop`) to get day-one boilerplate. Each top-level directory is the canonical location for that area of code.

## Layout

```
.
├── packages/
│   ├── runtime/
│   ├── sdk-py/
│   ├── gateway/
│   ├── kb-engine/
│   ├── eval-harness/
│   ├── observability/
│   ├── mcp-client/
│   └── channels/
│       ├── web/
│       ├── slack/
│       └── whatsapp/
├── apps/
│   ├── studio/             (Next.js)
│   └── control-plane/      (closed source, separate repo eventually)
├── cli/                    (Go)
├── examples/
├── infra/
│   ├── docker-compose.yml
│   ├── helm/
│   └── terraform/
├── .github/
│   └── workflows/
├── docs/
├── pyproject.toml          (uv workspace root)
├── Makefile
├── .pre-commit-config.yaml
├── .editorconfig
├── .gitignore
├── LICENSE                 (Apache 2.0)
└── README.md
```

## Bootstrap

```bash
git clone git@github.com:loop-ai/loop.git
cd loop
direnv allow
make bootstrap
make up
make migrate
make seed
make dev
```

See `engineering/HANDBOOK.md` for full conventions.
