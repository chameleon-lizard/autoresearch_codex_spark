# CLI documentation

Entry point script: `loop`.

Example:
- `loop run --max-iters 5`
- `loop run --max-iters 2 --limit 40`
- `loop report`
- `loop score configs/my_artifact.json`
- `loop reset`

All configuration is resolved from `config.load_config` through env/JSON file.
