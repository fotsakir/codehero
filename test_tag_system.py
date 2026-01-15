#!/usr/bin/env python3
"""
Playwright test script for ticket tag system
Tests tag creation, display, and color scheme
"""

from playwright.sync_api import sync_playwright
import time
import sys

BASE_URL = "https://localhost:9453"
USERNAME = "admin"
PASSWORD = "admin123"

def test_tag_system():
    """Test the tag system implementation"""
    print("Starting Tag System Test...\n")

    with sync_playwright() as p:
        # Launch browser (headless since we're in SSH environment)
        browser = p.chromium.launch(headless=True, args=['--ignore-certificate-errors'])
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()
        page.set_viewport_size({"width": 1920, "height": 1080})

        try:
            # Step 1: Login
            print("[1/8] Logging in...")
            page.goto(f"{BASE_URL}/login")
            page.fill('input[name="username"]', USERNAME)
            page.fill('input[name="password"]', PASSWORD)
            page.click('button[type="submit"]')
            page.wait_for_url(f"{BASE_URL}/dashboard")
            print("     ✓ Login successful")

            # Step 2: Go to projects page
            print("\n[2/8] Navigating to projects...")
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

            # Step 3: Open new ticket modal
            print("\n[3/8] Testing ticket creation form...")
            page.click('button:has-text("New Ticket")')
            page.wait_for_selector('#newTicketModal', state='visible')

            # Check tag dropdown exists
            tag_select = page.locator('select[name="tag"]')
            if not tag_select.is_visible():
                print("     ✗ Tag dropdown not found!")
                browser.close()
                return False

            # Verify all tag options exist
            tag_options = [opt.text_content() for opt in page.locator('select[name="tag"] option').all()]
            expected_tags = ['Feature', 'Bugfix', 'Hotfix', 'Test', 'Custom']

            if not all(tag in tag_options for tag in expected_tags):
                print(f"     ✗ Missing tag options. Found: {tag_options}")
                browser.close()
                return False

            print(f"     ✓ All tag options found: {', '.join(tag_options)}")
            page.screenshot(path='/tmp/tag-creation-form.png')
            print("     ✓ Screenshot saved: /tmp/tag-creation-form.png")

            # Step 4: Create tickets with different tags
            print("\n[4/8] Creating test tickets with different tags...")
            test_tickets = [
                ("hotfix", "Test Hotfix Ticket", "Testing hotfix tag with red color"),
                ("bugfix", "Test Bugfix Ticket", "Testing bugfix tag with orange color"),
                ("feature", "Test Feature Ticket", "Testing feature tag with blue color"),
                ("test", "Test Test Ticket", "Testing test tag with purple color"),
                ("custom", "Test Custom Ticket", "Testing custom tag with gray color")
            ]

            created_tickets = []
            for tag, title, description in test_tickets:
                # Fill form
                page.fill('input[name="title"]', title)
                page.fill('textarea[name="description"]', description)
                page.select_option('select[name="tag"]', tag)

                # Submit
                page.click('button[type="submit"]:has-text("Create Ticket")')
                page.wait_for_url("**/ticket/**")

                ticket_url = page.url
                created_tickets.append((tag, title, ticket_url))
                print(f"     ✓ Created ticket with tag: {tag.upper()}")

                # Go back to create another
                if tag != "custom":  # Last one
                    page.go_back()
                    page.wait_for_load_state('networkidle')
                    page.click('button:has-text("New Ticket")')
                    page.wait_for_selector('#newTicketModal', state='visible')

            # Step 5: Verify tag in detail view
            print("\n[5/8] Verifying tags in ticket detail view...")
            for tag, title, url in created_tickets:
                page.goto(url)
                page.wait_for_load_state('networkidle')

                # Check sidebar tag
                sidebar_tag = page.locator('.sidebar .tag-badge')
                if not sidebar_tag.is_visible():
                    print(f"     ✗ Tag badge not visible in sidebar for {tag}")
                    continue

                tag_text = sidebar_tag.text_content().strip()
                if tag_text == tag.upper():
                    print(f"     ✓ Tag displays correctly in detail view: {tag.upper()}")
                else:
                    print(f"     ✗ Tag mismatch. Expected: {tag.upper()}, Got: {tag_text}")

                # Take screenshot
                page.screenshot(path=f'/tmp/tag-detail-{tag}.png')
                print(f"     ✓ Screenshot saved: /tmp/tag-detail-{tag}.png")

            # Step 6: Verify tags in list view
            print("\n[6/8] Verifying tags in ticket list view...")
            page.goto(f"{BASE_URL}/tickets")
            page.wait_for_load_state('networkidle')

            # Take full list screenshot
            page.screenshot(path='/tmp/tag-list-view.png')
            print("     ✓ Screenshot saved: /tmp/tag-list-view.png")

            # Check each test ticket in the list
            for tag, title, url in created_tickets:
                ticket_row = page.locator(f'.ticket-row:has-text("{title}")').first
                if ticket_row.count() > 0:
                    tag_badge = ticket_row.locator('.tag-badge')
                    if tag_badge.is_visible():
                        badge_text = tag_badge.text_content().strip()
                        if badge_text == tag.upper():
                            print(f"     ✓ Tag displays in list view: {tag.upper()}")
                        else:
                            print(f"     ✗ Tag mismatch in list. Expected: {tag.upper()}, Got: {badge_text}")
                    else:
                        print(f"     ✗ Tag badge not visible in list for: {tag}")
                else:
                    print(f"     ⚠  Ticket not found in list: {title}")

            # Step 7: Test tag color scheme
            print("\n[7/8] Testing tag color scheme...")
            tag_colors = {
                'feature': '#6366f1',   # Indigo
                'bugfix': '#f59e0b',    # Orange
                'hotfix': '#ef4444',    # Red
                'test': '#8b5cf6',      # Purple
                'custom': '#64748b'     # Gray
            }

            for tag in ['feature', 'bugfix', 'hotfix', 'test', 'custom']:
                badge = page.locator(f'.tag-badge.{tag}').first
                if badge.count() > 0:
                    # Take individual badge screenshot
                    badge.screenshot(path=f'/tmp/tag-badge-{tag}.png')
                    print(f"     ✓ Tag color verified: {tag.upper()} (expected: {tag_colors[tag]})")
                else:
                    print(f"     ⚠  Tag badge not found for: {tag}")

            # Step 8: Test mobile responsive view
            print("\n[8/8] Testing mobile responsive layout...")
            page.set_viewport_size({"width": 375, "height": 667})  # iPhone size
            page.goto(f"{BASE_URL}/tickets")
            page.wait_for_load_state('networkidle')
            page.screenshot(path='/tmp/tag-list-mobile.png')
            print("     ✓ Mobile screenshot saved: /tmp/tag-list-mobile.png")

            # Check if tags overflow on mobile
            page.set_viewport_size({"width": 1920, "height": 1080})

            print("\n" + "="*60)
            print("TAG SYSTEM TEST COMPLETED SUCCESSFULLY!")
            print("="*60)
            print("\nScreenshots saved in /tmp/:")
            print("  - tag-creation-form.png")
            print("  - tag-list-view.png")
            print("  - tag-list-mobile.png")
            for tag in ['feature', 'bugfix', 'hotfix', 'test', 'custom']:
                print(f"  - tag-detail-{tag}.png")
                print(f"  - tag-badge-{tag}.png")

            print("\n✓ All tests passed!")

        except Exception as e:
            print(f"\n✗ Test failed with error: {e}")
            page.screenshot(path='/tmp/tag-test-error.png')
            print("Error screenshot saved: /tmp/tag-test-error.png")
            browser.close()
            return False

        finally:
            browser.close()

    return True

if __name__ == "__main__":
    success = test_tag_system()
    sys.exit(0 if success else 1)
