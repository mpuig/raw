"""Dashboard HTML generation for RAW server.

Separates HTML building logic from route handlers.
"""

from typing import Any


def build_approval_card(approval: dict[str, Any]) -> str:
    """Build HTML for a single approval card."""
    ctx_html = ""
    for k, v in approval["context"].items():
        ctx_html += (
            f'<div class="flex justify-between text-xs">'
            f'<span class="text-dark-500">{k}:</span> '
            f'<span class="text-brand-gray font-mono">{v}</span></div>'
        )

    buttons = ""
    for option in approval["options"]:
        if option == "approve":
            color_cls = "bg-brand-green hover:bg-green-600 text-white"
        elif option == "reject":
            color_cls = "bg-brand-red hover:bg-red-600 text-white"
        else:
            color_cls = "bg-dark-700 hover:bg-dark-600 text-brand-gray hover:text-white"

        buttons += (
            f'<button class="px-4 py-2 rounded text-sm font-medium transition-colors {color_cls}" '
            f'onclick="dashboard().approve(\'{approval["run_id"]}\', \'{approval["step_name"]}\')">'
            f'{option.title()}</button>'
        )

    return f"""
    <div class="bg-dark-800 border border-dark-600 rounded-lg p-5 flex flex-col shadow-lg shadow-black/20">
        <div class="flex justify-between items-start mb-4">
            <div>
                <h3 class="text-base font-bold text-white mb-1">{approval["workflow_id"]}</h3>
                <div class="text-xs font-mono text-dark-500">Step: {approval["step_name"]}</div>
            </div>
            <span class="bg-brand-yellow/10 text-brand-yellow text-xs px-2 py-1 rounded border border-brand-yellow/20 animate-pulse">
                Waiting
            </span>
        </div>

        <div class="bg-dark-900/50 rounded p-3 mb-4 border border-dark-700">
            <p class="text-sm text-gray-300 font-medium mb-2">{approval["prompt"]}</p>
            <div class="space-y-1 pt-2 border-t border-dark-700/50">
                {ctx_html}
            </div>
        </div>

        <div class="mt-auto flex gap-3">
            {buttons}
        </div>
    </div>
    """


def build_approvals_html(approvals: list[dict[str, Any]]) -> str:
    """Build HTML for all approval cards."""
    if not approvals:
        return ""
    return "".join(build_approval_card(a) for a in approvals)


def build_run_row(run: dict[str, Any]) -> str:
    """Build HTML for a single run table row."""
    status_colors = {
        "running": "bg-brand-blue/20 text-brand-blue",
        "waiting": "bg-brand-yellow/20 text-brand-yellow",
        "completed": "bg-brand-green/20 text-brand-green",
        "success": "bg-brand-green/20 text-brand-green",
        "failed": "bg-brand-red/20 text-brand-red",
        "stale": "bg-dark-600 text-dark-400",
    }
    status_cls = status_colors.get(run["status"], "bg-dark-700 text-brand-gray")

    mode_icon = (
        '<i class="fa-solid fa-network-wired" title="Connected"></i>'
        if run["mode"] == "connected"
        else '<i class="fa-solid fa-terminal" title="Subprocess"></i>'
    )

    return f"""
    <tr class="hover:bg-dark-700/50 transition-colors group">
        <td class="px-4 py-3 font-mono text-xs text-brand-gray group-hover:text-gray-300">{run["id"][:8]}...</td>
        <td class="px-4 py-3 text-gray-300 font-medium">{run["wf"]}</td>
        <td class="px-4 py-3">
            <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium {status_cls}">
                {run["status"]}
            </span>
        </td>
        <td class="px-4 py-3 text-brand-gray text-xs">{run["time"]}</td>
        <td class="px-4 py-3 text-right text-dark-500 text-xs">
            {mode_icon}
        </td>
    </tr>
    """


def build_runs_html(runs: list[dict[str, Any]]) -> str:
    """Build HTML for all run table rows."""
    if not runs:
        return ""
    return "".join(build_run_row(r) for r in runs)


def build_workflow_card(workflow: dict[str, Any]) -> str:
    """Build HTML for a single workflow card."""
    name = workflow.get("name", workflow.get("id", "unknown"))
    desc = workflow.get("intent", "No description provided.")
    if len(desc) > 60:
        desc = desc[:57] + "..."

    return f"""
    <div class="bg-dark-800 border border-dark-600 rounded-lg p-4 hover:border-brand-blue/50 transition-all hover:-translate-y-0.5 cursor-pointer group">
        <div class="flex items-center justify-between mb-3">
            <div class="w-8 h-8 rounded bg-dark-700 flex items-center justify-center text-brand-gray group-hover:text-brand-blue group-hover:bg-brand-blue/10 transition-colors">
                <i class="fa-solid fa-cube"></i>
            </div>
            <span class="text-[10px] uppercase font-bold text-dark-500 bg-dark-900 px-1.5 py-0.5 rounded border border-dark-700">DRAFT</span>
        </div>
        <h3 class="text-sm font-bold text-gray-200 group-hover:text-white truncate mb-1">{name}</h3>
        <p class="text-xs text-brand-gray leading-relaxed">{desc}</p>
    </div>
    """


def build_workflows_html(workflows: list[dict[str, Any]]) -> str:
    """Build HTML for all workflow cards."""
    if not workflows:
        return ""
    return "".join(build_workflow_card(w) for w in workflows)
