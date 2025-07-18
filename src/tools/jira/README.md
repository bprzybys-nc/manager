# Jira Integration Tool

This tool provides an API to interact with Jira, allowing you to perform actions such as adding comments to tickets and closing them.

## API Endpoints

- `GET /tickets/{ticket_id}`: Retrieves the description and comments from a specified Jira ticket.
- `POST /tickets/{ticket_id}/comments`: Adds a comment to a specified Jira ticket. The comment can be formatted.
- `PUT /tickets/{ticket_id}`: Closes a specified Jira ticket. You can optionally add a comment when closing.

### `POST /tickets/{ticket_id}/comments`

**Body**:

```json
{
  "comment": "This is a sample comment.",
  "formatting": "code"
}
```

- `formatting` (optional): Formats the comment text. Supported values are:
  - `bold`: For **bold** text.
  - `italic`: For _italic_ text.
  - `code`: For inline `code` snippets.
  - `code_block`: For larger {code} blocks.{code}

## Environment Variables

To run this tool, you need to set the following environment variables:

- `JIRA_URL`: The URL of your Jira instance (e.g., `https://your-domain.atlassian.net`).
- `JIRA_USERNAME`: The email address associated with your Jira account.
- `JIRA_API_TOKEN`: Your Jira API token.
