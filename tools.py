def get_mock_linkedin_data(name: str) -> dict:
    print(f"TOOL: Searching LinkedIn for {name}…")
    return {
        "source": "LinkedIn",
        "job_title": "Software Engineer",
        "company": "TechCorp",
        "name": name,
    }

def get_mock_github_data(name: str) -> dict:
    print(f"TOOL: Searching GitHub for {name}…")
    return {
        "source": "GitHub",
        "username": "shashwat46",
        "location": "Vellore",
        "name": name,
    }
