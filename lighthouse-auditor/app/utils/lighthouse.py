"""Lighthouse audit utilities and tools."""

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from pydantic import BaseModel


class LighthouseConfig(BaseModel):
    """Configuration for Lighthouse audit."""

    categories: List[str] = ["performance", "accessibility", "best-practices", "seo"]
    output_format: str = "json"
    only_categories: Optional[List[str]] = None
    chrome_flags: List[str] = ["--headless", "--no-sandbox"]
    throttling: Dict[str, Any] = {
        "cpuSlowdownMultiplier": 4,
        "networkSlowdownMultiplier": 2,
    }


@dataclass
class AuditIssue:
    """Represents a Lighthouse audit issue."""

    title: str
    description: str
    score: float
    impact: str
    suggestions: List[str]
    code_snippet: Optional[str] = None
    file_path: Optional[str] = None
    line_number: Optional[int] = None


class LighthouseRunner:
    """Handles running Lighthouse audits and processing results."""

    def __init__(self, config: Optional[LighthouseConfig] = None):
        self.config = config or LighthouseConfig()
        # Set environment variable for chrome-launcher
        chrome_path = "/usr/bin/google-chrome"
        os.environ["CHROME_PATH"] = chrome_path

    def run_audit(self, url: str, output_path: Optional[str] = None) -> Dict[str, Any]:
        """Run a Lighthouse audit on the specified URL.
        
        Args:
            url: The URL to audit
            output_path: Optional path to save the report. If not provided, a default will be used.
            
        Returns:
            Dict containing the audit results
        """

        run_timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        user_data_dir = Path("audits") / "tmp" / f"chrome-profile_{run_timestamp}"
        user_data_dir.mkdir(parents=True, exist_ok=True)
        absolute_user_data_path = user_data_dir.resolve()


        # Use absolute paths and additional Chrome flags
        chrome_launcher_config = {
            "chromePath": "/usr/bin/google-chrome",
            "chromeFlags": [
                "--headless",
                "--no-sandbox",
                "--disable-gpu",
                "--disable-dev-shm-usage",
                "--disable-software-rasterizer",
                f"--user-data-dir={absolute_user_data_path}",
            ],
        }

        # If no output path is provided, create a default one in the 'audits' directory
        if not output_path:
            # Sanitize URL to use as a filename
            parsed_url = urlparse(url)
            sanitized_filename = f"{parsed_url.netloc.replace('.', '_')}_{run_timestamp}.json"
            
            # Define the new audits directory relative to the current working directory
            audits_dir = Path("audits")
            audits_dir.mkdir(parents=True, exist_ok=True) # Ensure the directory exists
            output_path = audits_dir / sanitized_filename

        else:
            # Convert Windows-style paths to Linux if needed
            output_path = Path(str(output_path).replace('\\', '/'))
            if ':' in str(output_path):  # Remove Windows drive letter if present
                output_path = Path(str(output_path).split(':', 1)[1])
            # Ensure the output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

        # Get absolute path for lighthouse executable
        lighthouse_path = os.path.join(os.getcwd(), "node_modules", ".bin", "lighthouse")
        
        # Ensure output_path is absolute for the lighthouse command
        final_output_path = Path(output_path).resolve()

        print(f"Saving Lighthouse report to: {final_output_path}")

        command = [
            lighthouse_path,
            url,
            "--output=json",
            f"--output-path={final_output_path}",
            f"--chrome-flags={' '.join(chrome_launcher_config['chromeFlags'])}",
            "--quiet",
        ]

        # Add categories if specified
        if self.config.only_categories:
            command.append("--only-categories=" + ",".join(self.config.only_categories))

        try:
            print("Executing command:", " ".join(command))
            subprocess.run(command, capture_output=True, text=True, check=True)
            
            # Since we are now always saving to a file, read the result from the file
            if final_output_path.exists():
                with open(final_output_path, 'r') as f:
                    return json.load(f)
            else:
                 raise RuntimeError("Lighthouse ran but the output file was not found.")

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Lighthouse audit failed. Error: {e.stderr}\nOutput: {e.stdout}")
        except json.JSONDecodeError:
            raise RuntimeError(f"Failed to parse Lighthouse output from file: {final_output_path}")

    def extract_issues(self, report: Union[str, Dict[str, Any]]) -> List[AuditIssue]:
        """Extract actionable issues from a Lighthouse report.
        
        Args:
            report: Either a JSON string or dict containing the Lighthouse report
            
        Returns:
            List of AuditIssue objects
        """
        if isinstance(report, str):
            try:
                report_data = json.loads(report)
            except json.JSONDecodeError:
                raise ValueError("Invalid JSON report")
        else:
            report_data = report

        issues = []
        audits = report_data.get("audits", {})

        for audit_id, audit_data in audits.items():
            if audit_data.get("score", 1) is not None and audit_data.get("score", 1) < 1:  # Only process failed audits
                issue = AuditIssue(
                    title=audit_data.get("title", "Unknown Issue"),
                    description=audit_data.get("description", ""),
                    score=audit_data.get("score", 0),
                    impact=self._calculate_impact(audit_data),
                    suggestions=self._extract_suggestions(audit_data),
                    code_snippet=self._extract_code_snippet(audit_data),
                )
                issues.append(issue)

        return issues

    def _calculate_impact(self, audit_data: Dict[str, Any]) -> str:
        """Calculate the impact level of an audit issue."""
        score = audit_data.get("score", 0)
        weight = audit_data.get("weight", 0)

        if score < 0.5 and weight > 3:
            return "high"
        elif score < 0.8:
            return "medium"
        else:
            return "low"

    def _extract_suggestions(self, audit_data: Dict[str, Any]) -> List[str]:
        """Extract improvement suggestions from audit data."""
        suggestions = []

        # Extract from description
        if "description" in audit_data:
            suggestions.append(audit_data["description"])

        # Extract from details
        details = audit_data.get("details", {})
        if "items" in details:
            for item in details["items"]:
                if isinstance(item, dict):
                    for key in ["suggestion", "recommendation", "message"]:
                        if key in item:
                            suggestions.append(item[key])

        return list(set(suggestions))  # Remove duplicates

    def _extract_code_snippet(self, audit_data: Dict[str, Any]) -> Optional[str]:
        """Extract relevant code snippet from audit data if available."""
        details = audit_data.get("details", {})

        # Try to find code snippets in items
        if "items" in details:
            for item in details["items"]:
                if isinstance(item, dict):
                    # Look for common code-related fields
                    for key in ["snippet", "source", "code"]:
                        if key in item:
                            # Clean HTML if present
                            snippet = item[key]
                            if isinstance(snippet, str):
                                soup = BeautifulSoup(snippet, "html.parser")
                                return soup.get_text()
                            return str(snippet)

        return None


class ReportChunker:
    """Handles chunking large Lighthouse reports into manageable pieces."""

    @staticmethod
    def chunk_report(
        report: Dict[str, Any], max_chunk_size: int = 8000
    ) -> List[Dict[str, Any]]:
        """Split a large report into smaller chunks while maintaining context.
        
        Args:
            report: The full Lighthouse report
            max_chunk_size: Maximum size of each chunk in characters
            
        Returns:
            List of report chunks
        """
        chunks = []
        current_chunk = {"metadata": report.get("metadata", {}), "audits": {}}
        current_size = 0

        for audit_id, audit_data in report.get("audits", {}).items():
            # Estimate size of this audit
            audit_size = len(json.dumps(audit_data))

            # If adding this audit would exceed chunk size, start a new chunk
            if current_size + audit_size > max_chunk_size and current_chunk["audits"]:
                chunks.append(current_chunk)
                current_chunk = {"metadata": report.get("metadata", {}), "audits": {}}
                current_size = 0

            # Add audit to current chunk
            current_chunk["audits"][audit_id] = audit_data
            current_size += audit_size

        # Add final chunk if not empty
        if current_chunk["audits"]:
            chunks.append(current_chunk)

        return chunks
