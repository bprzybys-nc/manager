import os
from enum import Enum
from typing import Optional

from jira import JIRA


class JiraFormatting(str, Enum):
    BOLD = "bold"        # *bold*
    ITALIC = "italic"    # _italic_
    CODE = "code"        # `code`
    CODE_BLOCK = "code_block"  # {code}...{code}

class JiraClient:

    def __init__(self):
        jira_url = os.environ["JIRA_URL"]
        jira_user = os.environ["JIRA_USERNAME"]
        jira_token = os.environ["JIRA_API_TOKEN"]
        self.client = JIRA(server=jira_url, basic_auth=(jira_user, jira_token))
    
    def add_comment(self, ticket_id: str, comment: str, formatting: Optional["JiraFormatting"] = None) -> None:
        formatted_comment = self._format_comment(comment, formatting)
        self.client.add_comment(ticket_id, formatted_comment)

    def close_ticket(self, ticket_id: str, comment: str = None, formatting: Optional[JiraFormatting] = None) -> None:
        if comment:
            formatted_comment = self._format_comment(comment, formatting)
            self.add_comment(ticket_id, formatted_comment)
        # The transition name ('Done', 'Closed', etc.) depends on your specific Jira workflow.
        # You may need to adjust this value.
        try:
            self.client.transition_issue(ticket_id, 'Done')
        except Exception as e:
            print(f"Could not find transition 'Done', trying 'Closed'. Error: {e}")
            self.client.transition_issue(ticket_id, 'Closed')

    def get_ticket_details(self, ticket_id: str) -> dict:
        """
        Retrieves the description and all comments from a Jira ticket.

        :param issue_id: The ID of the Jira issue (e.g., 'PROJ-123').
        :return: A dictionary with 'description' and 'comments'.
        """
        issue = self.client.issue(ticket_id)

        description = issue.fields.description

        comments = []
        # Check if comments exist before trying to iterate
        if issue.fields.comment and hasattr(issue.fields.comment, 'comments'):
            for comment in issue.fields.comment.comments:
                comments.append(f"{comment.author.displayName}: {comment.body}")

        return {
            "description": description,
            "comments": comments
        }

    def _format_comment(self,message: str, formatting: JiraFormatting) -> str:
        if formatting is None:
            return message
        if formatting == JiraFormatting.BOLD:
            return f"*{message}*"
        elif formatting == JiraFormatting.ITALIC:
            return f"_{message}_"
        elif formatting == JiraFormatting.CODE:
            return f"{{code}}{message}{{code}}"
        elif formatting == JiraFormatting.CODE_BLOCK:
            return f"```{message}```"
        # Add more formatting options as needed    

        return message
