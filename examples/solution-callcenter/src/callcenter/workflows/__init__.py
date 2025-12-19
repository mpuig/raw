"""Workflows for call center automation.

Workflows are autonomous agents that run after conversations end to handle
post-call tasks like summarization, CRM updates, and follow-up actions.
"""

from callcenter.workflows.post_call import PostCallWorkflow

__all__ = ["PostCallWorkflow"]
