"""
Octopus AI — Plan Tentacle 🗺️
Lets the agent draft and maintain a live, step-by-step task plan (todo list)
that streams to the UI as a checklist. Encourages structured, multi-step work.
"""
from tools import BaseTool


class PlanTool(BaseTool):
    name = "update_plan"
    category = "plan"
    description = (
        "Create or update a step-by-step plan (todo list) for a complex, multi-step "
        "request. Call this first to outline your approach, then call it again to update "
        "step statuses as you make progress. Always send the COMPLETE ordered list each time. "
        "This surfaces a live checklist to the user."
    )
    parameters = {
        "type": "object",
        "properties": {
            "steps": {
                "type": "array",
                "description": "The full ordered list of plan steps (send the complete list every time).",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Short description of the step"},
                        "status": {
                            "type": "string",
                            "enum": ["pending", "in_progress", "done"],
                            "description": "Current status of the step",
                        },
                    },
                    "required": ["title", "status"],
                },
            }
        },
        "required": ["steps"],
    }

    async def execute(self, steps=None, **kwargs) -> dict:
        steps = steps or []
        valid = {"pending", "in_progress", "done"}
        normalized = []
        for s in steps:
            if isinstance(s, dict):
                status = s.get("status", "pending")
                normalized.append({
                    "title": str(s.get("title", "")).strip(),
                    "status": status if status in valid else "pending",
                })
            else:
                normalized.append({"title": str(s).strip(), "status": "pending"})

        done = sum(1 for s in normalized if s["status"] == "done")
        return {
            "status": "success",
            "plan": normalized,
            "summary": f"{done}/{len(normalized)} steps completed",
        }
