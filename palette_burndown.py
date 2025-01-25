import requests
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import json
import os

from dotenv import load_dotenv

load_dotenv(verbose=True)

# GitHub API Configuration
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
ORG = os.getenv('ORG')
PROJECT_TITLE = os.getenv('PROJECT_TITLE')


HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Content-Type": "application/json",
}

START_DATE = datetime(2025, 1, 12)
END_DATE = datetime(2025, 1, 25)

BURNDOWN_IMAGE_FILE_NAME = "palette_burndown.png"

QUERY = """
query($org: String!, $cursor: String) {
  organization(login: $org) {
    projectsV2(first: 100) {
      nodes {
        title
        items(first: 50, after: $cursor) {
          nodes {
            id
            fieldValues(first: 10) {
              nodes {
                ... on ProjectV2ItemFieldTextValue {
                  text
                  field {
                    ... on ProjectV2FieldCommon {
                      name
                    }
                  }
                }
                ... on ProjectV2ItemFieldNumberValue {
                  number
                  field {
                    ... on ProjectV2FieldCommon {
                      name
                    }
                  }
                }
              }
            }
            content {
              ... on Issue {
                title
                state
                closedAt
              }
            }
          }
          pageInfo {
            hasNextPage
            endCursor
          }
        }
      }
    }
  }
}

"""


def fetch_project_items(org, project_title):
    """Fetch project items for a given organization and filter by project title."""
    url = "https://api.github.com/graphql"
    variables = {"org": org, "cursor": None}
    all_items = []

    while True:
        response = requests.post(
            url, json={"query": QUERY, "variables": variables}, headers=HEADERS
        )
        response.raise_for_status()
        data = response.json()

        # Check for errors
        if "errors" in data:
            print("GraphQL Errors:", data["errors"])
            raise RuntimeError("GraphQL query failed.")

        # Check if 'data' is present
        if "data" not in data:
            print("Response JSON:", json.dumps(data, indent=2))
            raise ValueError("Unexpected response structure: 'data' key missing.")

        # Navigate to projects
        projects = data["data"]["organization"]["projectsV2"]["nodes"]
        project = next((p for p in projects if p["title"] == project_title), None)
        if not project:
            raise ValueError(f"Project '{project_title}' not found in organization '{org}'.")

        # Fetch items from the project
        project_items = project["items"]
        all_items.extend(project_items["nodes"])

        # Handle pagination
        if not project_items["pageInfo"]["hasNextPage"]:
            break
        variables["cursor"] = project_items["pageInfo"]["endCursor"]

    return all_items


def process_items(items, milestone_name):
    """Process project items to extract useful fields like Estimate and closure dates."""
    processed_items = []
    for item in items:
        fields = {}
        for field in item.get("fieldValues", {}).get("nodes", []):
            # Safely handle missing 'field' key
            field_metadata = field.get("field")
            if not field_metadata:
                print(f"Skipping field with missing metadata: {field}")
                continue

            # Extract field name and value
            field_name = field_metadata.get("name", "Unknown")
            field_value = field.get("text") or field.get("number")
            fields[field_name] = field_value

        # Extract issue details
        content = item.get("content", {})
        title = content.get("title", "No Title")
        state = content.get("state", "Unknown")
        closed_at = content.get("closedAt", None)

        # Add to processed list
        processed_items.append({
            "title": title,
            "state": state,
            "closed_at": closed_at,
            "fields": fields,
        })

    return processed_items


def calculate_by_date(items, field_name=None):
    """Calculate completed tasks or estimates grouped by closure date."""
    closed_per_day = {}
    for item in items:
        # Use count (1) if field_name is None, or the specific field value otherwise
        value = 1 if field_name is None else item["fields"].get(field_name, 0)
        if value and item["state"] == "CLOSED" and item["closed_at"]:
            closed_date = datetime.strptime(item["closed_at"], "%Y-%m-%dT%H:%M:%SZ").date()
            closed_per_day[closed_date] = closed_per_day.get(closed_date, 0) + float(value)
    return closed_per_day


def generate_burndown_chart(closed_per_day, start_date, end_date, total_value, ylabel,
                            filename=BURNDOWN_IMAGE_FILE_NAME, color="green"):
    """Generate and display the burndown chart."""
    # Generate the date range
    date_range = [start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)]

    # Ideal burndown (linear progression)
    ideal_burndown = [total_value - (total_value / len(date_range)) * i for i in range(len(date_range))]

    # Actual burndown
    remaining_value = total_value
    actual_burndown = []

    for current_date in date_range:
        current_date = current_date.date()
        completed_today = closed_per_day.get(current_date, 0)
        remaining_value -= completed_today
        actual_burndown.append(remaining_value)

        # Debug output for verification
        print(f"Date: {current_date}, Completed: {completed_today}, Remaining: {remaining_value}")

    # Plotting the chart
    plt.figure(figsize=(10, 6))
    plt.plot(date_range, ideal_burndown, label="Ideal Burndown", linestyle="--", color="gray")
    plt.plot(date_range, actual_burndown, label="Actual Burndown", marker="o", color=color)
    plt.fill_between(date_range, actual_burndown, ideal_burndown, color=color, alpha=0.1)
    plt.title("Palette Burndown Chart")
    plt.xlabel("Date")
    plt.ylabel(ylabel)
    plt.legend()
    plt.grid(True)

    # Save the chart as a PNG file
    plt.savefig(filename, format="png", dpi=300)
    print(f"Chart saved as {filename}")

    plt.show()


def main():
    # Fetch and process project items
    items = fetch_project_items(ORG, PROJECT_TITLE)
    processed_items = process_items(items, "Sprint 4")

    # Task count burndown
    total_tasks = len(processed_items)
    closed_tasks_per_day = calculate_by_date(processed_items)
    print(f"Total Tasks: {total_tasks}, Closed Tasks Per Day: {closed_tasks_per_day}")
    generate_burndown_chart(closed_tasks_per_day, START_DATE, END_DATE, total_tasks, "Remaining Tasks",
                            "burndown_tasks.png", "blue")

    # Size estimate burndown
    total_estimate = sum(
        float(item["fields"].get("Estimate", 0)) for item in processed_items if "Estimate" in item["fields"]
    )
    closed_estimates_per_day = calculate_by_date(processed_items, "Estimate")
    print(f"Total Estimate: {total_estimate}, Closed Estimates Per Day: {closed_estimates_per_day}")
    generate_burndown_chart(closed_estimates_per_day, START_DATE, END_DATE, total_estimate, "Remaining Estimate",
                            "burndown_estimates.png")


if __name__ == "__main__":
    main()
