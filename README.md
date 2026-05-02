# avi-claude-forge

A Claude Code marketplace of plugins, skills, and agents for orchestrating Claude Code workflows.

## Plugins

| Plugin | Purpose |
|---|---|
| [`telegram-tower`](./plugins/telegram-tower) | Spawn, list, resume, and kill Claude Code sessions with Remote Control enabled. Telegram-driven dispatcher pattern. |

## Install

```
/plugin marketplace add avijit90/avi-claude-forge
/plugin install telegram-tower@avi-claude-forge
```

After install, run `/reload-plugins` to activate.

## Update

```
/plugin marketplace update avi-claude-forge
```

## Repo layout

```
avi-claude-forge/
├── .claude-plugin/
│   └── marketplace.json     # catalog
├── plugins/
│   └── telegram-tower/
│       ├── .claude-plugin/plugin.json
│       ├── commands/
│       └── README.md
├── README.md
└── LICENSE
```

## License

MIT — see [LICENSE](./LICENSE).
