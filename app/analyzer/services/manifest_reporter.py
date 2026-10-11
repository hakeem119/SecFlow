# pyrefly: ignore [missing-import]
import html
import json
from pathlib import Path
from typing import Any


def render_manifest_html(manifest_data: dict[str, Any]) -> str:
    """
    Renders a standalone, responsive HTML dashboard for the ProjectManifest.
    Safely visualizes architecture, endpoints, secrets, technologies, and actors.
    """
    project = manifest_data.get("project", {})
    actors = manifest_data.get("actors", [])
    technologies = manifest_data.get("technologies", [])
    architecture = manifest_data.get("architecture", {})
    deployment = manifest_data.get("deployment", {})
    dependencies = manifest_data.get("key_dependencies", [])
    confidence = manifest_data.get("confidence_score", 0.0)
    secrets = manifest_data.get("secrets", [])
    endpoints = manifest_data.get("endpoints", [])
    global_middlewares = architecture.get("global_middlewares", [])

    # Dynamic Sanitized Text Values
    proj_name = html.escape(str(project.get("name", "Unknown Project")))
    proj_type = html.escape(str(project.get("type", "N/A")))
    proj_desc = html.escape(str(project.get("description", "No description provided.")))
    proj_purpose = html.escape(str(project.get("primary_purpose", "N/A")))
    arch_pattern = html.escape(str(architecture.get("pattern", "N/A")))
    data_flow = html.escape(str(architecture.get("data_flow_summary", "N/A")))

    # 1. Actors Rows
    actors_html = "".join(
        f"<tr><td><strong>{html.escape(str(a.get('name', '')))}</strong></td>"
        f"<td>{html.escape(str(a.get('role', '')))}</td></tr>"
        for a in actors if isinstance(a, dict)
    ) or "<tr><td colspan='2' class='text-muted'>No actors identified</td></tr>"

  # 2. Tech Stack Pills (مع دعم الـ version لو موجود)
    tech_pills_list = []
    for t in technologies:
        if isinstance(t, dict):
            name = html.escape(str(t.get("name", "")))
            cat = html.escape(str(t.get("category", "tech")))
            ver = (
                f" @ {html.escape(str(t.get('version')))}"
                if t.get("version")
                else ""
            )
            tech_pills_list.append(
                f"<span class='tech-pill'>{name} <small>({cat}{ver})</small></span>"
            )
    tech_pills = (
        "".join(tech_pills_list)
        or "<span class='text-muted'>No technologies mapped</span>"
    )
    # 3. Entry Points & Components
    entry_points = "".join(
        f"<li><code>{html.escape(str(ep))}</code></li>"
        for ep in architecture.get("entry_points", [])
    ) or "<li class='text-muted'>None identified</li>"

    components = "".join(
        f"<li>{html.escape(str(c))}</li>"
        for c in architecture.get("core_components", [])
    ) or "<li class='text-muted'>None identified</li>"

    # 4. Global Middlewares
    middlewares_html = "".join(
        f"<li><strong>{html.escape(str(m.get('name', '')))}</strong> "
        f"<span class='badge badge-gray'>{html.escape(str(m.get('type', 'filter')))}</span>: "
        f"{html.escape(str(m.get('description', '')))}</li>"
        for m in global_middlewares if isinstance(m, dict)
    ) or "<li class='text-muted'>None identified</li>"

    # 5. Dependencies (دعم مزدوج: نصوص عادية أو Dictionaries فيها Version)
    deps_rendered = []
    for d in dependencies:
        if isinstance(d, dict):
            name = html.escape(str(d.get("name", "")))
            ver = f" <small style='color:var(--muted)'>v{html.escape(str(d.get('version')))}</small>" if d.get("version") else ""
            dev = " <span class='badge badge-gray'>dev</span>" if d.get("is_dev") else ""
            deps_rendered.append(f"<code class='dep-pill'>{name}{ver}{dev}</code>")
        else:
            deps_rendered.append(f"<code class='dep-pill'>{html.escape(str(d))}</code>")
    deps_html = " ".join(deps_rendered) or "<span class='text-muted'>None recorded</span>"

    # 6. Endpoints Table (لو وجدت)
    endpoints_rows = []
    for ep in endpoints:
        if not isinstance(ep, dict):
            continue
        method = html.escape(str(ep.get("method", "GET"))).upper()
        method_cls = f"badge-method-{method.lower()}" if method.lower() in ["get", "post", "put", "delete", "ws"] else "badge-gray"
        auth_req = ep.get("auth_required", False)
        auth_method = ep.get("auth_method")
        auth_badge = (
            f"<span class='badge badge-auth'>🔒 Auth ({html.escape(str(auth_method))})</span>"
            if auth_req else "<span class='badge badge-public'>🌐 Public</span>"
        )
        inputs = ", ".join(ep.get("input_types", [])) or "none"
        mws = ", ".join(ep.get("middlewares", [])) or "-"
        endpoints_rows.append(
            f"<tr>"
            f"<td><span class='badge {method_cls}'>{method}</span> <code>{html.escape(str(ep.get('path', '')))}</code></td>"
            f"<td>{auth_badge}</td>"
            f"<td><small>{html.escape(inputs)}</small></td>"
            f"<td><small>{html.escape(mws)}</small></td>"
            f"<td>{html.escape(str(ep.get('description', '')))}</td>"
            f"</tr>"
        )
    endpoints_html = "".join(endpoints_rows) or "<tr><td colspan='5' class='text-muted'>No endpoints exposed or recorded</td></tr>"

    # 7. Secrets Table (لو وجدت)
    secrets_rows = []
    for s in secrets:
        if not isinstance(s, dict):
            continue
        s_name = html.escape(str(s.get("name", "")))
        s_type = html.escape(str(s.get("type", "credential")))
        s_file = html.escape(str(s.get("file_path", "")))
        s_line = f" (Line {s.get('line_start')})" if s.get("line_start") else ""
        s_desc = html.escape(str(s.get("description", "")))
        secrets_rows.append(
            f"<tr>"
            f"<td><code>{s_name}</code></td>"
            f"<td><span class='badge badge-danger'>{s_type}</span></td>"
            f"<td><code>{s_file}{s_line}</code></td>"
            f"<td>{s_desc}</td>"
            f"</tr>"
        )
    secrets_html = "".join(secrets_rows) or "<tr><td colspan='4' class='text-muted'>No sensitive secrets or fallback credentials detected.</td></tr>"

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
      --danger: #f87171;
      --warning: #fbbf24;
    }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: var(--bg);
      color: var(--text);
      margin: 0;
      padding: 24px;
    }}
    .container {{ max-width: 1200px; margin: 0 auto; }}
    header {{ border-bottom: 1px solid var(--border); padding-bottom: 16px; margin-bottom: 24px; }}
    h1 {{ margin: 0 0 8px 0; font-size: 28px; color: var(--accent); }}
    .badge {{
      display: inline-block;
      padding: 4px 10px;
      border-radius: 9999px;
      font-size: 12px;
      font-weight: bold;
      background: #0369a1;
      color: #bae6fd;
    }}
    .badge-gray {{ background: #334155; color: #cbd5e1; }}
    .badge-auth {{ background: #831843; color: #fbcfe8; }}
    .badge-public {{ background: #065f46; color: #a7f3d0; }}
    .badge-danger {{ background: #7f1d1d; color: #fecaca; }}
    .badge-method-get {{ background: #065f46; color: #a7f3d0; }}
    .badge-method-post {{ background: #854d0e; color: #fef08a; }}
    .badge-method-delete {{ background: #991b1b; color: #fee2e2; }}
    .badge-method-put {{ background: #1e40af; color: #dbeafe; }}
    .badge-method-ws {{ background: #581c87; color: #e9d5ff; }}
    .confidence-badge {{ background: #065f46; color: #a7f3d0; }}
    .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; }}
    .card {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 20px;
      margin-bottom: 20px;
    }}
    h2 {{ font-size: 18px; margin-top: 0; border-bottom: 1px solid var(--border); padding-bottom: 8px; color: var(--accent); }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
    th, td {{ text-align: left; padding: 10px 8px; border-bottom: 1px solid var(--border); font-size: 13px; }}
    th {{ color: var(--muted); font-size: 12px; text-transform: uppercase; }}
    .tech-pill {{
      display: inline-block;
      background: #334155;
      color: #f8fafc;
      padding: 4px 10px;
      margin: 4px;
      border-radius: 6px;
      font-size: 13px;
    }}
    .dep-pill {{
      display: inline-block;
      margin: 3px;
      padding: 3px 8px;
      border: 1px solid var(--border);
      border-radius: 4px;
    }}
    code {{ background: #0f172a; padding: 2px 6px; border-radius: 4px; color: #f472b6; }}
    ul {{ margin: 8px 0; padding-left: 20px; font-size: 14px; }}
    .text-muted {{ color: var(--muted); }}
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
        <p><strong>Global Middlewares:</strong></p>
        <ul>{middlewares_html}</ul>
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

    <!-- API Endpoints Section -->
    <div class="card">
      <h2>Discovered API Attack Surface & Endpoints</h2>
      <table>
        <thead>
          <tr>
            <th>Endpoint</th>
            <th>Access</th>
            <th>Input Parameters</th>
            <th>Middlewares</th>
            <th>Description</th>
          </tr>
        </thead>
        <tbody>
          {endpoints_html}
        </tbody>
      </table>
    </div>

    <!-- Secrets & Credentials Section -->
    <div class="card">
      <h2>Sensitive Configurations & Credentials</h2>
      <table>
        <thead>
          <tr>
            <th>Secret Name</th>
            <th>Storage Mechanism</th>
            <th>Observed Location</th>
            <th>Description</th>
          </tr>
        </thead>
        <tbody>
          {secrets_html}
        </tbody>
      </table>
    </div>

    <div class="card">
      <h2>Technology Stack & Dependencies</h2>
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