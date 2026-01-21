"""
HeroAgent Screenshot Tool

Take screenshots using Playwright.
"""

import os
from typing import Dict, Any, Optional

from .base import BaseTool, ToolResult

try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False


class ScreenshotTool(BaseTool):
    """Take screenshots of web pages."""

    name = "Screenshot"
    description = "Take screenshots of a web page (desktop and/or mobile). Uses Playwright with full_page=True."

    VIEWPORTS = {
        'desktop': {'width': 1920, 'height': 1080},
        'mobile': {'width': 375, 'height': 667},
        'tablet': {'width': 768, 'height': 1024},
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.timeout = self.config.get('timeout', 30000)
        self.wait_time = self.config.get('wait_time', 2000)

    def execute(
        self,
        url: str,
        output: Optional[str] = None,
        viewport: str = "both",
        full_page: bool = True,
        **kwargs
    ) -> ToolResult:
        """Take screenshot(s) of a web page.

        Args:
            url: URL to screenshot
            output: Output path (without extension for 'both' mode)
            viewport: 'desktop', 'mobile', 'tablet', or 'both' (desktop+mobile)
            full_page: Capture full page (default True per global context rules)

        Returns:
            ToolResult with screenshot path(s)
        """
        if not HAS_PLAYWRIGHT:
            return ToolResult(
                output="Error: Playwright not installed. Run: pip install playwright && playwright install chromium",
                is_error=True
            )

        if not url:
            return ToolResult(output="Error: No URL provided", is_error=True)

        # Default output path
        if not output:
            output = "/tmp/screenshot"

        # Ensure output directory exists
        output_dir = os.path.dirname(output) if os.path.dirname(output) else "."
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # Remove extension if provided (we'll add it)
        if output.endswith('.png'):
            output = output[:-4]

        screenshots_taken = []

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch()
                context = browser.new_context(ignore_https_errors=True)
                page = context.new_page()

                # Navigate
                page.goto(url, timeout=self.timeout)
                page.wait_for_load_state("networkidle")
                page.wait_for_timeout(self.wait_time)  # Wait for animations

                # Determine viewports to capture
                if viewport == "both":
                    viewports_to_capture = ['desktop', 'mobile']
                else:
                    viewports_to_capture = [viewport]

                for vp_name in viewports_to_capture:
                    vp = self.VIEWPORTS.get(vp_name, self.VIEWPORTS['desktop'])
                    page.set_viewport_size(vp)

                    # Build output filename
                    if len(viewports_to_capture) > 1:
                        out_path = f"{output}_{vp_name}.png"
                    else:
                        out_path = f"{output}.png"

                    page.screenshot(path=out_path, full_page=full_page)
                    screenshots_taken.append(out_path)

                browser.close()

            if len(screenshots_taken) == 1:
                return ToolResult(
                    output=f"Screenshot saved: {screenshots_taken[0]}",
                    metadata={'paths': screenshots_taken}
                )
            else:
                return ToolResult(
                    output=f"Screenshots saved:\n- " + "\n- ".join(screenshots_taken),
                    metadata={'paths': screenshots_taken}
                )

        except Exception as e:
            return ToolResult(output=f"Error taking screenshot: {str(e)}", is_error=True)

    def get_schema(self) -> Dict[str, Any]:
        """Get tool schema."""
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL to screenshot"
                },
                "output": {
                    "type": "string",
                    "description": "Output path (without extension). Default: /tmp/screenshot"
                },
                "viewport": {
                    "type": "string",
                    "enum": ["desktop", "mobile", "tablet", "both"],
                    "description": "Viewport size. 'both' captures desktop and mobile. Default: both"
                },
                "full_page": {
                    "type": "boolean",
                    "description": "Capture full page scroll. Default: true"
                }
            },
            "required": ["url"]
        }
