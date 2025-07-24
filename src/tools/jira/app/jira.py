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

    def add_internal_comment(self, ticket_id: str, comment: str, formatting: Optional["JiraFormatting"] = None) -> None:
        """Add an internal comment with clear marking for agent/staff visibility only.
        
        Note: True internal-only comments require Jira Service Management.
        For regular Jira projects, this adds a clearly marked system comment.
        """
        formatted_comment = self._format_comment(comment, formatting)
        
        # First try to determine if this is a Service Desk issue
        try:
            issue = self.client.issue(ticket_id)
            is_service_desk = hasattr(issue.fields, 'customfield_10010') or \
                             'Service Desk' in str(issue.fields.issuetype) or \
                             any('servicedesk' in str(f).lower() for f in dir(issue.fields))
        except Exception:
            is_service_desk = False
        
        if is_service_desk:
            # Try Service Management API for true internal comments
            try:
                comment_data = {'body': formatted_comment, 'public': False}
                response = self.client._session.post(
                    f"{self.client.server_url}/rest/servicedeskapi/request/{issue.id}/comment",
                    json=comment_data
                )
                if response.status_code in [200, 201]:
                    return
            except Exception:
                pass
        
        # For regular Jira projects or when Service Desk API fails:
        # Add comment with clear internal marking
        internal_marked_comment = f"🔒 *[INTERNAL - SYSTEM GENERATED]*\n\n{formatted_comment}\n\n---\n*This comment contains automated system information for internal use.*"
        
        try:
            self.client.add_comment(ticket_id, internal_marked_comment)
        except Exception as e:
            raise Exception(f"Failed to add internal comment: {e}")

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

    def get_ticket(self, ticket_id: str) -> dict:
        """
        Retrieves full ticket data matching standard Jira API structure.
        
        :param ticket_id: The ID of the Jira issue (e.g., 'PROJ-123').
        :return: A dictionary with 'fields' containing full ticket data.
        """
        issue = self.client.issue(ticket_id)
        
        return {
            "fields": {
                "summary": issue.fields.summary,
                "description": issue.fields.description,
                "project": {"key": issue.fields.project.key},
                "issuetype": {"name": issue.fields.issuetype.name},
                "priority": {"name": issue.fields.priority.name if issue.fields.priority else "None"},
                "assignee": {"displayName": issue.fields.assignee.displayName if issue.fields.assignee else "Unassigned"},
                "status": {"name": issue.fields.status.name},
                "created": issue.fields.created,
                "labels": issue.fields.labels if issue.fields.labels else []
            }
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
