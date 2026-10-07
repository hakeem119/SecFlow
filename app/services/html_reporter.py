import json
from typing import Any


def generate_html_report(snapshot_data: dict[str, Any]) -> str:
    """
    Generate a responsive HTML report with a premium glassmorphism UI for the snapshot data.
    """
    json_data = json.dumps(snapshot_data)
    
    html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SecFlow Repository Analysis Report</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/vue@2.6.14/dist/vue.js"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        body { background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%); color: #f8fafc; font-family: 'Inter', sans-serif; min-height: 100vh; }
        .glass-panel { 
            background: rgba(30, 41, 59, 0.4); 
            backdrop-filter: blur(12px); 
            border: 1px solid rgba(255, 255, 255, 0.08); 
            border-radius: 16px; 
            box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.5);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }
        .glass-panel:hover {
            transform: translateY(-2px);
            box-shadow: 0 20px 40px -10px rgba(0, 0, 0, 0.6);
            border: 1px solid rgba(255, 255, 255, 0.15);
        }
        .status-success { color: #10b981; filter: drop-shadow(0 0 8px rgba(16, 185, 129, 0.4)); }
        .status-partial { color: #f59e0b; filter: drop-shadow(0 0 8px rgba(245, 158, 11, 0.4)); }
        .status-error { color: #ef4444; filter: drop-shadow(0 0 8px rgba(239, 68, 68, 0.4)); }
        
        /* Custom Scrollbar */
        ::-webkit-scrollbar { width: 8px; }
        ::-webkit-scrollbar-track { background: rgba(0, 0, 0, 0.1); border-radius: 4px; }
        ::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.1); border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: rgba(255, 255, 255, 0.2); }
    </style>
</head>
<body class="p-4 md:p-8">
    <div id="app" class="max-w-7xl mx-auto space-y-8">
        <!-- Header -->
        <header class="flex flex-col md:flex-row justify-between items-center glass-panel p-8">
            <div class="mb-4 md:mb-0">
                <h1 class="text-4xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 via-indigo-400 to-emerald-400 mb-2">
                    <i class="fas fa-shield-alt mr-3 text-indigo-400"></i>SecFlow Analysis Report
                </h1>
                <p class="text-slate-300 text-lg">Repository: <a :href="report.repository.url" target="_blank" class="text-blue-400 hover:text-blue-300 transition-colors underline decoration-blue-400/30 underline-offset-4">{{ report.repository.name }}</a></p>
                <div class="flex items-center gap-4 mt-3 text-sm text-slate-400">
                    <span class="bg-slate-800/50 px-3 py-1 rounded-full border border-slate-700"><i class="fas fa-code-branch mr-2 text-slate-500"></i>{{ report.repository.commit.substring(0, 7) }}</span>
                    <span class="bg-slate-800/50 px-3 py-1 rounded-full border border-slate-700"><i class="fas fa-fingerprint mr-2 text-slate-500"></i>{{ report.workspace.id }}</span>
                </div>
            </div>
            <div class="text-left md:text-right bg-slate-800/30 p-4 rounded-xl border border-slate-700/50">
                <p class="text-slate-400 text-sm mb-1 uppercase tracking-wider font-semibold">Generated At</p>
                <p class="font-mono text-emerald-400 text-lg">{{ new Date(report.generated_at).toLocaleString() }}</p>
            </div>
        </header>

        <div class="grid grid-cols-1 lg:grid-cols-12 gap-8">
            <!-- Metrics Sidebar -->
            <div class="lg:col-span-4 space-y-8">
                <!-- Code Metrics -->
                <div class="glass-panel p-6">
                    <h2 class="text-xl font-bold mb-6 text-slate-100 flex items-center"><i class="fas fa-chart-pie mr-3 text-emerald-400"></i>Code Metrics</h2>
                    <div class="space-y-4">
                        <div class="flex justify-between items-center p-3 rounded-lg bg-slate-800/50 border border-slate-700/50">
                            <span class="text-slate-400">Total Lines of Code</span>
                            <span class="font-mono font-bold text-lg text-slate-200">{{ report.metrics.loc.toLocaleString() }}</span>
                        </div>
                        <div class="flex justify-between items-center p-3 rounded-lg bg-slate-800/50 border border-slate-700/50">
                            <span class="text-slate-400">Complexity Score</span>
                            <span class="font-mono font-bold text-lg text-amber-400">{{ report.metrics.complexity }}</span>
                        </div>
                        <div class="flex justify-between items-center p-3 rounded-lg bg-slate-800/50 border border-slate-700/50">
                            <span class="text-slate-400">Total Files</span>
                            <span class="font-mono font-bold text-lg text-blue-400">{{ report.structure.files.length.toLocaleString() }}</span>
                        </div>
                    </div>
                </div>
                
                <!-- Warnings -->
                <div class="glass-panel p-6">
                    <h2 class="text-xl font-bold mb-6 text-slate-100 flex items-center"><i class="fas fa-exclamation-circle text-amber-500 mr-3"></i>Warnings</h2>
                    <ul v-if="report.warnings.length > 0" class="space-y-3">
                        <li v-for="(warning, index) in report.warnings" :key="index" class="p-3 bg-amber-500/10 rounded-lg text-amber-200 text-sm border border-amber-500/20 flex items-start">
                            <i class="fas fa-exclamation-triangle mt-1 mr-2 text-amber-500/70"></i>
                            <span>{{ warning }}</span>
                        </li>
                    </ul>
                    <div v-else class="text-center py-6 text-slate-500">
                        <i class="fas fa-check-circle text-3xl mb-2 text-slate-600"></i>
                        <p class="italic">No warnings reported.</p>
                    </div>
                </div>
            </div>
            
            <!-- Main Content -->
            <div class="lg:col-span-8 space-y-8">
                <!-- Tool Status -->
                <div class="glass-panel p-6">
                    <h2 class="text-xl font-bold mb-6 text-slate-100 flex items-center"><i class="fas fa-robot mr-3 text-blue-400"></i>Tool Pipeline Status</h2>
                    <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-4">
                        <div v-for="(status, tool) in report.tool_status" :key="tool" class="text-center p-4 rounded-xl bg-slate-800/50 border border-slate-700/50 hover:bg-slate-800 transition-colors">
                            <div class="h-12 flex items-center justify-center mb-2">
                                <i v-if="status === 'success'" class="fas fa-check-circle text-3xl status-success"></i>
                                <i v-else-if="status === 'partial'" class="fas fa-exclamation-triangle text-3xl status-partial"></i>
                                <i v-else class="fas fa-times-circle text-3xl status-error"></i>
                            </div>
                            <p class="text-sm font-semibold text-slate-300 capitalize">{{ tool }}</p>
                        </div>
                    </div>
                </div>

                <!-- Findings Grid -->
                <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
                    <!-- Security Findings -->
                    <div class="glass-panel p-6 relative overflow-hidden">
                        <div class="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-red-500 to-orange-500"></div>
                        <h2 class="text-xl font-bold mb-6 text-slate-100 flex justify-between items-center">
                            <span class="flex items-center"><i class="fas fa-bug mr-3 text-red-400"></i>Security Findings</span>
                            <span class="bg-red-500/20 text-red-300 py-1 px-3 rounded-full text-sm font-bold">{{ report.security_evidence.semgrep.length }}</span>
                        </h2>
                        <div class="overflow-y-auto max-h-[400px] pr-2 space-y-3">
                            <div v-if="report.security_evidence.semgrep.length > 0">
                                <div v-for="(finding, idx) in report.security_evidence.semgrep" :key="idx" class="p-4 bg-slate-800/50 rounded-lg border border-slate-700/50 hover:border-slate-600 transition-colors mb-3">
                                    <div class="flex justify-between items-start mb-3">
                                        <span class="font-mono text-sm font-bold text-red-400 break-words pr-2">{{ finding.rule_id }}</span>
                                        <span class="text-xs px-2 py-1 rounded bg-red-500/20 border border-red-500/30 text-red-300 shrink-0">{{ finding.severity }}</span>
                                    </div>
                                    <div class="flex items-center text-sm text-slate-400 bg-slate-900/50 p-2 rounded">
                                        <i class="fas fa-file-code mr-2 text-slate-500"></i>
                                        <span class="truncate" :title="finding.path">{{ finding.path }}</span>
                                        <span class="ml-2 text-slate-500 font-mono">L{{ finding.line }}</span>
                                    </div>
                                </div>
                            </div>
                            <div v-else class="flex flex-col items-center justify-center py-12 text-slate-500">
                                <i class="fas fa-shield-check text-4xl mb-3 text-slate-600"></i>
                                <p class="italic">No security findings detected.</p>
                            </div>
                        </div>
                    </div>

                    <!-- Secret Findings -->
                    <div class="glass-panel p-6 relative overflow-hidden">
                        <div class="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-purple-500 to-pink-500"></div>
                        <h2 class="text-xl font-bold mb-6 text-slate-100 flex justify-between items-center">
                            <span class="flex items-center"><i class="fas fa-key mr-3 text-purple-400"></i>Secrets</span>
                            <span class="bg-purple-500/20 text-purple-300 py-1 px-3 rounded-full text-sm font-bold">{{ report.secret_findings.count }}</span>
                        </h2>
                        <div class="overflow-y-auto max-h-[400px] pr-2 space-y-3">
                            <div v-if="report.secret_findings.count > 0">
                                <div v-for="(secret, idx) in report.secret_findings.findings" :key="idx" class="p-4 bg-slate-800/50 rounded-lg border border-slate-700/50 hover:border-slate-600 transition-colors mb-3">
                                    <div class="flex justify-between items-start mb-3">
                                        <span class="font-mono text-sm font-bold text-purple-400">{{ secret.detector || 'Exposed Secret' }}</span>
                                    </div>
                                    <div class="flex items-center text-sm text-slate-400 bg-slate-900/50 p-2 rounded">
                                        <i class="fas fa-file-code mr-2 text-slate-500"></i>
                                        <span class="truncate" :title="secret.path">{{ secret.path }}</span>
                                        <span class="ml-2 text-slate-500 font-mono">L{{ secret.line }}</span>
                                    </div>
                                </div>
                            </div>
                            <div v-else class="flex flex-col items-center justify-center py-12 text-slate-500">
                                <i class="fas fa-lock text-4xl mb-3 text-slate-600"></i>
                                <p class="italic">No secrets detected.</p>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Dependencies (Full Width) -->
                <div class="glass-panel p-6">
                    <h2 class="text-xl font-bold mb-6 text-slate-100 flex justify-between items-center">
                        <span class="flex items-center"><i class="fas fa-box-open mr-3 text-blue-400"></i>Software Supply Chain</span>
                        <span class="bg-blue-500/20 text-blue-300 py-1 px-3 rounded-full text-sm font-bold">{{ report.dependencies.packages.length }} Packages</span>
                    </h2>
                    
                    <div v-if="report.dependencies.packages.length > 0" class="overflow-hidden rounded-xl border border-slate-700/50">
                        <div class="overflow-x-auto">
                            <table class="w-full text-left border-collapse">
                                <thead>
                                    <tr class="bg-slate-800/80 text-slate-300 text-sm uppercase tracking-wider">
                                        <th class="p-4 border-b border-slate-700/50 font-semibold">Package Name</th>
                                        <th class="p-4 border-b border-slate-700/50 font-semibold">Version</th>
                                        <th class="p-4 border-b border-slate-700/50 font-semibold hidden md:table-cell">Ecosystem</th>
                                    </tr>
                                </thead>
                                <tbody class="text-sm text-slate-300 max-h-[300px] overflow-y-auto block w-full table-caption" style="display: table-row-group;">
                                    <tr v-for="(pkg, idx) in report.dependencies.packages" :key="idx" class="border-b border-slate-700/30 hover:bg-slate-800/30 transition-colors">
                                        <td class="p-4 font-mono text-slate-200"><i class="fas fa-cube mr-2 text-slate-500 text-xs"></i>{{ pkg.name }}</td>
                                        <td class="p-4 text-emerald-400 font-mono">{{ pkg.version }}</td>
                                        <td class="p-4 hidden md:table-cell text-slate-400">{{ pkg.ecosystem }}</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                    <div v-else class="flex flex-col items-center justify-center py-12 text-slate-500 bg-slate-800/30 rounded-xl border border-slate-700/50">
                        <i class="fas fa-ghost text-4xl mb-3 text-slate-600"></i>
                        <p class="italic">No dependencies discovered.</p>
                    </div>
                </div>
            </div>
        </div>
        
        <footer class="text-center text-slate-500 text-sm py-8">
            <p>SecFlow Analysis Engine &copy; 2026. All rights reserved.</p>
        </footer>
    </div>

    <script>
        const reportData = __JSON_DATA_PLACEHOLDER__;
        new Vue({
            el: '#app',
            data: {
                report: reportData
            }
        });
    </script>
</body>
</html>"""

    return html.replace("__JSON_DATA_PLACEHOLDER__", json_data)
