# Case Template Representation Viewer

This is a small static UI to view templates (from `templates/`) and example case JSON files (from `cases/extracted/`). It shows the selected template on the left and a selected example on the right, with highlights for missing/extra fields.

How to run

1. From the repo root run a simple static server (Python recommended):

```powershell
python -m http.server 8000
```

2. Open the viewer in your browser:

```
http://localhost:8000/case_template_representation/index.html
```

Notes
- The page attempts to auto-discover templates from `/templates/templates.json` and standalone files (like `ipc_397.json`).
- Example files are discovered from `/cases/extracted/` (it parses the directory listing served by `python -m http.server`).
- The viewer is read-only and neutral-styled for non-technical users.

If you want, I can commit these files to `dev-haystack` and open a PR to `main`.
