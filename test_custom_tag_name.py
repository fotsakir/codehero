#!/usr/bin/env python3
"""
Test script for custom tag name functionality
Tests creating tickets with custom tag names and verifying display
"""

from playwright.sync_api import sync_playwright
import time
import sys

BASE_URL = "https://localhost:9453"
USERNAME = "admin"
PASSWORD = "admin123"

def test_custom_tag_name():
    """Test the custom tag name implementation"""
    print("Starting Custom Tag Name Test...\n")

    with sync_playwright() as p:
        # Launch browser
        browser = p.chromium.launch(headless=True, args=['--ignore-certificate-errors'])
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()
        page.set_viewport_size({"width": 1920, "height": 1080})

        try:
            # Step 1: Login
            print("[1/6] Logging in...")
            page.goto(f"{BASE_URL}/login")
            page.fill('input[name="username"]', USERNAME)
            page.fill('input[name="password"]', PASSWORD)
            page.click('button[type="submit"]')
            page.wait_for_url(f"{BASE_URL}/dashboard")
            print("     ✓ Login successful")

            # Step 2: Go to projects page
            print("\n[2/6] Navigating to projects...")
            page.goto(f"{BASE_URL}/projects")
            page.wait_for_load_state('networkidle')

            # Check if there are any projects
            projects = page.locator('.card a').count()
            if projects == 0:
                print("     ✗ No projects found. Please create a project first.")
                browser.close()
                return False

            # Click first project
            page.locator('.card a').first.click()
            page.wait_for_load_state('networkidle')
            print("     ✓ Project opened")

            # Step 3: Open new ticket modal and test conditional input
            print("\n[3/6] Testing custom tag name input field...")
            page.click('button:has-text("New Ticket")')
            page.wait_for_selector('#newTicketModal', state='visible')

            # Verify custom tag name input is hidden initially
            custom_input = page.locator('#customTagNameGroup')
            if custom_input.is_visible():
                print("     ✗ Custom tag name input should be hidden by default!")
                browser.close()
                return False
            print("     ✓ Custom tag name input hidden by default")

            # Select 'custom' tag
            page.select_option('select[name="tag"]', 'custom')
            time.sleep(0.5)  # Wait for JS to show the input

            # Verify custom tag name input is now visible
            if not custom_input.is_visible():
                print("     ✗ Custom tag name input should be visible when 'custom' is selected!")
                browser.close()
                return False
            print("     ✓ Custom tag name input appears when 'custom' selected")

            # Take screenshot of form with custom input
            page.screenshot(path='/tmp/custom-tag-form.png')
            print("     ✓ Screenshot saved: /tmp/custom-tag-form.png")

            # Step 4: Create tickets with custom tag names
            print("\n[4/6] Creating test tickets with custom tag names...")
            test_tickets = [
                ("Documentation", "Update API documentation"),
                ("Research", "Research new framework options"),
                ("Refactor", "Refactor auth module"),
            ]

            created_tickets = []
            for custom_name, title in test_tickets:
                # Fill form
                page.fill('input[name="title"]', title)
                page.fill('textarea[name="description"]', f"Testing custom tag name: {custom_name}")
                page.select_option('select[name="tag"]', 'custom')
                time.sleep(0.3)  # Wait for custom input to appear
                page.fill('input[name="tag_custom_name"]', custom_name)

                # Submit
                page.click('button[type="submit"]:has-text("Create Ticket")')
                page.wait_for_url("**/ticket/**")

                ticket_url = page.url
                created_tickets.append((custom_name, title, ticket_url))
                print(f"     ✓ Created ticket with custom tag: {custom_name}")

                # Go back to create another
                if custom_name != "Refactor":  # Last one
                    page.go_back()
                    page.wait_for_load_state('networkidle')
                    page.click('button:has-text("New Ticket")')
                    page.wait_for_selector('#newTicketModal', state='visible')

            # Step 5: Verify custom tag names in detail view
            print("\n[5/6] Verifying custom tag names in ticket detail view...")
            for custom_name, title, url in created_tickets:
                page.goto(url)
                page.wait_for_load_state('networkidle')

                # Check sidebar tag badge shows custom name
                sidebar_tag = page.locator('.sidebar .tag-badge')
                if not sidebar_tag.is_visible():
                    print(f"     ✗ Tag badge not visible in sidebar for {custom_name}")
                    continue

                tag_text = sidebar_tag.text_content().strip()
                if tag_text == custom_name.upper():
                    print(f"     ✓ Custom tag name displays correctly: {custom_name.upper()}")
                else:
                    print(f"     ✗ Tag mismatch. Expected: {custom_name.upper()}, Got: {tag_text}")

                # Take screenshot
                page.screenshot(path=f'/tmp/custom-tag-detail-{custom_name.lower()}.png')
                print(f"     ✓ Screenshot saved: /tmp/custom-tag-detail-{custom_name.lower()}.png")

            # Step 6: Verify custom tag names in list view
            print("\n[6/6] Verifying custom tag names in ticket list view...")
            page.goto(f"{BASE_URL}/tickets")
            page.wait_for_load_state('networkidle')

            # Take full list screenshot
            page.screenshot(path='/tmp/custom-tag-list-view.png')
            print("     ✓ Screenshot saved: /tmp/custom-tag-list-view.png")

            # Check each test ticket in the list
            for custom_name, title, url in created_tickets:
                ticket_row = page.locator(f'.ticket-row:has-text("{title}")').first
                if ticket_row.count() > 0:
                    tag_badge = ticket_row.locator('.tag-badge')
                    if tag_badge.is_visible():
                        badge_text = tag_badge.text_content().strip()
                        if badge_text == custom_name.upper():
                            print(f"     ✓ Custom tag displays in list: {custom_name.upper()}")
                        else:
                            print(f"     ✗ Tag mismatch in list. Expected: {custom_name.upper()}, Got: {badge_text}")
                    else:
                        print(f"     ✗ Tag badge not visible in list for: {custom_name}")
                else:
                    print(f"     ⚠  Ticket not found in list: {title}")

            print("\n" + "="*60)
            print("CUSTOM TAG NAME TEST COMPLETED SUCCESSFULLY!")
            print("="*60)
            print("\nScreenshots saved in /tmp/:")
            print("  - custom-tag-form.png")
            print("  - custom-tag-list-view.png")
            for custom_name, _, _ in created_tickets:
                print(f"  - custom-tag-detail-{custom_name.lower()}.png")

            print("\n✓ All tests passed!")

        except Exception as e:
            print(f"\n✗ Test failed with error: {e}")
            import traceback
            traceback.print_exc()
            page.screenshot(path='/tmp/custom-tag-test-error.png')
            print("Error screenshot saved: /tmp/custom-tag-test-error.png")
            browser.close()
            return False

        finally:
            browser.close()

    return True

if __name__ == "__main__":
    success = test_custom_tag_name()
    sys.exit(0 if success else 1)
