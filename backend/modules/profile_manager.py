"""
profile_manager.py — THING Jarvis Upgrade
Handles reading and updating the user's personal profile.
"""

import json
import os
from typing import Any, Dict, List

PROFILE_PATH = os.path.join("backend", "data", "personal_profile.json")

class ProfileManager:
    def __init__(self):
        self.profile = self._load_profile()

    def _load_profile(self) -> Dict[str, Any]:
        if not os.path.exists(PROFILE_PATH):
            return {}
        try:
            with open(PROFILE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[Profile] Error loading: {e}")
            return {}

    def reload(self):
        """Reloads profile from disk."""
        self.profile = self._load_profile()

    def save_profile(self):
        try:
            with open(PROFILE_PATH, "w") as f:
                json.dump(self.profile, f, indent=4)
        except Exception as e:
            print(f"[Profile] Error saving: {e}")

    def update_info(self, key: str, value: Any):
        """Updates a top-level field in the profile."""
        if key in self.profile and isinstance(self.profile[key], list):
            if value not in self.profile[key]:
                self.profile[key].append(value)
        else:
            self.profile[key] = value
        self.save_profile()

    def add_project(self, name: str, description: str):
        project = {"name": name, "description": description}
        if "projects" not in self.profile:
            self.profile["projects"] = []
        self.profile["projects"].append(project)
        self.save_profile()

    def get_summary(self) -> str:
        """Returns a string summary for the LLM system prompt."""
        self.reload()
        profile = self.profile
        summary = f"User: {profile.get('name')} ({profile.get('nickname')})\n"
        summary += f"Role: {profile.get('role', 'User')}\n"
        
        # Education
        edu = profile.get('education', {})
        if isinstance(edu, dict):
            summary += f"Education: {edu.get('degree')} at {edu.get('college')} ({edu.get('status')})\n"
        else:
            summary += f"Education: {edu}\n"

        # Skills
        skills = profile.get('skills', {})
        if isinstance(skills, dict):
            langs = ", ".join(skills.get('programming_languages', []))
            domains = ", ".join(skills.get('domains', []))
            summary += f"Skills: {langs} | Domains: {domains}\n"
        else:
            summary += f"Skills: {', '.join(skills)}\n"

        # Projects (Top 10 to keep prompt lean)
        projects = [p['name'] for p in profile.get('projects', [])]
        summary += f"Key Projects: {', '.join(projects[:10])} (Total: {len(projects)})\n"
        
        # Goals
        summary += f"Primary Goals: {', '.join(profile.get('goals', [])[:5])}\n"
        
        # Personality
        pers = profile.get('personality', {})
        if pers:
            summary += f"Work Style: {pers.get('work_style')}\n"

        return summary

# Singleton
profile_manager = ProfileManager()
