# avi-claude-forge

Avi's personal Claude Code marketplace.

A curated collection of plugins, skills, and agents for orchestrating Claude Code workflows. Built first for personal use; public so others can clone and adapt anything that fits.

## Plugins

| Plugin | Purpose |
|---|---|
| [`telegram-tower`](./plugins/telegram-tower) | Spawn, list, resume, and kill Claude Code sessions with Remote Control enabled. Telegram-driven dispatcher pattern. |

## Install

Add the marketplace, then install plugins individually:

```
/plugin marketplace add avijit90/avi-claude-forge
/plugin install telegram-tower@avi-claude-forge
```

For local development against a clone:

```
/plugin marketplace add /path/to/avi-claude-forge
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
│   └── telegram-tower/      # first plugin
│       ├── .claude-plugin/plugin.json
│       ├── commands/
│       └── README.md
├── README.md
└── LICENSE
```

## License

MIT — see [LICENSE](./LICENSE).
