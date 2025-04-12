from pathlib import Path
from datetime import datetime
import json
from typing import Dict, Optional
from playwright.async_api import Page, CDPSession, Error as PlaywrightError

class PageDataCollector:
    """
    Utility class for collecting webpage data including screenshots and HTML.
    
    This class captures both visual and structural data from web pages:
    - Full page screenshots (PNG format)
    - Complete page content including resources (MHTML format)
    - Metadata about the capture (JSON format)
    
    Example:
        ```python
        from playwright.async_api import async_playwright
        
        collector = PageDataCollector()
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            
            # Navigate and capture
            await page.goto('https://example.com')
            metadata = await collector.capture_page_data(
                page,
                task="login_form_detection"
            )
        ```
    """
    
    def __init__(self, output_dir: Optional[Path] = None):
        """
        Initialize the collector with an output directory.
        
        Args:
            output_dir: Path to store captured data. Defaults to "screen_shots_data"
                      in the current working directory.
        """
        self.output_dir = output_dir or Path("screen_shots_data")
        self.output_dir.mkdir(exist_ok=True)
    
    async def capture_page_data(self, page: Page, task: Optional[str] = None, url: Optional[str] = None) -> Dict[str, str]:
        """
        Capture page screenshot and HTML/resources for the current page state.
        
        Args:
            page: Playwright page object to capture
            task: Description of what the page represents (e.g., "login_form")
            url: Optional URL to record in metadata (defaults to page.url)
            
        Returns:
            Dictionary containing:
            - task: Optional task description
            - url: Page URL
            - timestamp: Capture timestamp
            - screenshot_path: Path to the PNG screenshot
            - mhtml_path: Path to the MHTML content
            - viewport: Page viewport size
            
        Raises:
            PlaywrightError: If screenshot or CDP operations fail
        """
        screenshot_path = None
        mhtml_path = None
        metadata_path = None
        
        try:
            # Generate timestamp for unique filenames
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Get current URL if not provided
            url = url or page.url
            
            # Take screenshot
            screenshot_path = self.output_dir / f"screenshot_{timestamp}.png"
            await page.screenshot(path=str(screenshot_path), full_page=True)
            
            # Use Chrome DevTools Protocol (CDP) to capture complete page content
            # CDP allows direct communication with the browser to access advanced features
            # Here we use it to get a snapshot that includes all page resources (HTML, CSS, images)
            cdp_session = await page.context.new_cdp_session(page)
            try:
                mhtml_data = await cdp_session.send("Page.captureSnapshot")
                
                # Save the captured content as MHTML (web archive format that includes all resources)
                mhtml_path = self.output_dir / f"page_{timestamp}.mhtml"
                mhtml_path.write_text(mhtml_data["data"], encoding="utf-8")
            finally:
                await cdp_session.detach()  # Clean up CDP session
            
            # Save metadata
            metadata = {
                "task": task,
                "url": url,           
                "timestamp": timestamp,
                "screenshot_path": str(screenshot_path),
                "mhtml_path": str(mhtml_path)
            }
            metadata_path = self.output_dir / f"metadata_{timestamp}.json"
            metadata_path.write_text(json.dumps(metadata, indent=2))
            
            return metadata
            
        except Exception as e:
            # Clean up any partially created files
            for path in [p for p in [screenshot_path, mhtml_path, metadata_path] if p and p.exists()]:
                path.unlink()
            raise Exception(f"Failed to capture page data: {str(e)}")
