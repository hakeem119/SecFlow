# pyrefly: ignore [missing-import]
import html
import json
from pathlib import Path
from typing import Any


def render_manifest_html(manifest_data: dict[str, Any]) -> str:
    """
    Renders a standalone, responsive HTML dashboard for the ProjectManifest.
    Visualizes architecture, technology stack, actors, components, and evidence.
    """
    project = manifest_data.get("project", {})
    actors = manifest_data.get("actors", [])
    technologies = manifest_data.get("technologies", [])
    architecture = manifest_data.get("architecture", {})
    deployment = manifest_data.get("deployment", {})
    dependencies = manifest_data.get("key_dependencies", [])
    confidence = manifest_data.get("confidence_score", 0.0)

    # Sanitize dynamic values
    proj_name = html.escape(str(project.get("name", "Unknown Project")))
    proj_type = html.escape(str(project.get("type", "N/A")))
    proj_desc = html.escape(str(project.get("description", "No description provided.")))
    proj_purpose = html.escape(str(project.get("primary_purpose", "N/A")))
    arch_pattern = html.escape(str(architecture.get("pattern", "N/A")))
    data_flow = html.escape(str(architecture.get("data_flow_summary", "N/A")))

    # Render actors rows
    actors_html = "".join(
        f"<tr><td><strong>{html.escape(str(a.get('name', '')))}</strong></td>"
        f"<td>{html.escape(str(a.get('role', '')))}</td></tr>"
        for a in actors
    ) or "<tr><td colspan='2'>No actors identified</td></tr>"

    # Render tech stack pills
    tech_pills = "".join(
        f"<span class='tech-pill'>{html.escape(str(t.get('name', '')))} "
        f"<small>({html.escape(str(t.get('category', '')))})</small></span>"
        for t in technologies
    ) or "<span>No technologies mapped</span>"

    # Render entry points & components
    entry_points = "".join(
        f"<li><code>{html.escape(str(ep))}</code></li>"
        for ep in architecture.get("entry_points", [])
    ) or "<li>None identified</li>"

    components = "".join(
        f"<li>{html.escape(str(c))}</li>"
        for c in architecture.get("core_components", [])
    ) or "<li>None identified</li>"

    # Render dependencies list
    deps_html = "".join(
        f"<code>{html.escape(str(d))}</code> "
        for d in dependencies
    ) or "None recorded"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>SecFlow Manifest Dashboard - {proj_name}</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    :root {{
      --bg: #0f172a;
      --card-bg: #1e293b;
      --text: #f8fafc;
      --muted: #94a3b8;
      --accent: #38bdf8;
      --border: #334155;
      --success: #34d399;
    }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: var(--bg);
      color: var(--text);
      margin: 0;
      padding: 24px;
    }}
    .container {{ max-width: 1100px; margin: 0 auto; }}
    header {{ border-bottom: 1px solid var(--border); padding-bottom: 16px; margin-bottom: 24px; }}
    h1 {{ margin: 0 0 8px 0; font-size: 28px; color: var(--accent); }}
    .badge {{
      display: inline-block;
      padding: 4px 12px;
      border-radius: 9999px;
      font-size: 12px;
      font-weight: bold;
      background: #0369a1;
      color: #bae6fd;
    }}
    .confidence-badge {{ background: #065f46; color: #a7f3d0; }}
    .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; }}
    .card {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 20px;
    }}
    h2 {{ font-size: 18px; margin-top: 0; border-bottom: 1px solid var(--border); padding-bottom: 8px; color: var(--accent); }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
    th, td {{ text-align: left; padding: 8px; border-bottom: 1px solid var(--border); font-size: 14px; }}
    .tech-pill {{
      display: inline-block;
      background: #334155;
      color: #f8fafc;
      padding: 4px 10px;
      margin: 4px;
      border-radius: 6px;
      font-size: 13px;
    }}
    code {{ background: #0f172a; padding: 2px 6px; border-radius: 4px; color: #f472b6; }}
    ul {{ margin: 8px 0; padding-left: 20px; font-size: 14px; }}
  </style>
</head>
<body>
  <div class="container">
    <header>
      <h1>{proj_name}</h1>
      <span class="badge">{proj_type}</span>
      <span class="badge confidence-badge">Confidence: {int(confidence * 100)}%</span>
      <p style="color: var(--muted); margin-top: 12px;">{proj_desc}</p>
      <p><strong>Primary Purpose:</strong> {proj_purpose}</p>
    </header>

    <div class="grid">
      <div class="card">
        <h2>Architecture & Workflow</h2>
        <p><strong>Pattern:</strong> {arch_pattern}</p>
        <p><strong>Data Flow:</strong> {data_flow}</p>
        <p><strong>Entry Points:</strong></p>
        <ul>{entry_points}</ul>
        <p><strong>Core Components:</strong></p>
        <ul>{components}</ul>
      </div>

      <div class="card">
        <h2>Actors & Roles</h2>
        <table>
          <thead>
            <tr><th>Actor</th><th>Role / Permissions</th></tr>
          </thead>
          <tbody>
            {actors_html}
          </tbody>
        </table>
      </div>
    </div>

    <div class="card" style="margin-bottom: 20px;">
      <h2>Technology Stack</h2>
      <div>{tech_pills}</div>
      <h3 style="font-size: 14px; margin-top: 16px; color: var(--muted);">Key Dependencies:</h3>
      <div>{deps_html}</div>
    </div>

    <div class="card">
      <h2>Deployment</h2>
      <p><strong>Containerized:</strong> {'Yes' if deployment.get('containerized') else 'No'}</p>
      <p><strong>Configs:</strong> {', '.join(deployment.get('configs', [])) or 'None'}</p>
      <p><strong>Target Platforms:</strong> {', '.join(deployment.get('target_platforms', [])) or 'None'}</p>
    </div>
  </div>
</body>
</html>
"""


def save_manifest_artifacts(workspace_path: str, manifest_data: dict[str, Any]) -> dict[str, str]:
    """
    Serializes and persists project_manifest.json and manifest.html inside workspace.
    """
    ws = Path(workspace_path)
    json_path = ws / "project_manifest.json"
    html_path = ws / "manifest.html"

    # Write JSON manifest
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2, ensure_ascii=False)

    # Write HTML dashboard
    html_content = render_manifest_html(manifest_data)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    return {
        "manifest_json": str(json_path),
        "manifest_html": str(html_path),
    }