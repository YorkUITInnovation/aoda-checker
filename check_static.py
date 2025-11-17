#!/usr/bin/env python
"""
Static HTML Accessibility Checker - Works without browser automation!
Analyzes HTML for basic WCAG 2.1 AA compliance issues.
"""
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import sys
from datetime import datetime
from collections import Counter

class StaticAccessibilityChecker:
    """Check accessibility without browser automation."""

    def __init__(self, url):
        self.url = url
        self.issues = []
        self.warnings = []
        self.passes = []

    def check(self):
        """Run all accessibility checks."""
        print(f"🔍 Analyzing: {self.url}")
        print("=" * 70)

        try:
            # Fetch the page
            print("\n1. Fetching HTML...")
            response = requests.get(self.url, timeout=10)
            response.raise_for_status()
            print(f"   ✓ Status: {response.status_code}")

            # Parse HTML
            print("\n2. Parsing HTML...")
            soup = BeautifulSoup(response.text, 'html.parser')
            print(f"   ✓ HTML parsed successfully")

            # Run checks
            print("\n3. Running accessibility checks...")
            self._check_images(soup)
            self._check_headings(soup)
            self._check_forms(soup)
            self._check_links(soup)
            self._check_language(soup)
            self._check_page_title(soup)
            self._check_landmarks(soup)
            self._check_buttons(soup)

            # Display results
            self._display_results()

        except Exception as e:
            print(f"\n❌ Error: {e}")
            sys.exit(1)

    def _check_images(self, soup):
        """Check images for alt text."""
        images = soup.find_all('img')
        images_without_alt = [img for img in images if not img.get('alt')]

        if images_without_alt:
            self.issues.append({
                'rule': 'Images must have alt text',
                'impact': 'critical',
                'count': len(images_without_alt),
                'description': f'{len(images_without_alt)} images missing alt attributes'
            })
        else:
            self.passes.append('All images have alt text')

    def _check_headings(self, soup):
        """Check heading structure."""
        headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        h1_count = len(soup.find_all('h1'))

        if h1_count == 0:
            self.issues.append({
                'rule': 'Page must have one H1 heading',
                'impact': 'serious',
                'count': 1,
                'description': 'No H1 heading found'
            })
        elif h1_count > 1:
            self.warnings.append({
                'rule': 'Page should have only one H1',
                'impact': 'moderate',
                'count': h1_count,
                'description': f'Multiple H1 headings found ({h1_count})'
            })
        else:
            self.passes.append('Proper H1 heading structure')

        # Check heading order
        levels = [int(h.name[1]) for h in headings]
        for i in range(len(levels) - 1):
            if levels[i+1] - levels[i] > 1:
                self.warnings.append({
                    'rule': 'Heading levels should not skip',
                    'impact': 'moderate',
                    'count': 1,
                    'description': f'Heading skips from H{levels[i]} to H{levels[i+1]}'
                })
                break

    def _check_forms(self, soup):
        """Check form inputs for labels."""
        inputs = soup.find_all(['input', 'select', 'textarea'])
        inputs_without_labels = []

        for inp in inputs:
            input_id = inp.get('id')
            input_type = inp.get('type', 'text')

            # Skip hidden inputs
            if input_type in ['hidden', 'submit', 'button']:
                continue

            # Check for label or aria-label
            has_label = False
            if input_id:
                label = soup.find('label', {'for': input_id})
                if label:
                    has_label = True

            if not has_label and not inp.get('aria-label') and not inp.get('aria-labelledby'):
                inputs_without_labels.append(inp)

        if inputs_without_labels:
            self.issues.append({
                'rule': 'Form inputs must have labels',
                'impact': 'critical',
                'count': len(inputs_without_labels),
                'description': f'{len(inputs_without_labels)} form inputs missing labels'
            })
        else:
            self.passes.append('All form inputs have labels')

    def _check_links(self, soup):
        """Check links for accessibility."""
        links = soup.find_all('a')
        empty_links = [link for link in links if not link.get_text(strip=True) and not link.get('aria-label')]

        if empty_links:
            self.issues.append({
                'rule': 'Links must have discernible text',
                'impact': 'serious',
                'count': len(empty_links),
                'description': f'{len(empty_links)} links have no text'
            })
        else:
            self.passes.append('All links have text')

    def _check_language(self, soup):
        """Check if html lang attribute is set."""
        html = soup.find('html')
        if not html or not html.get('lang'):
            self.issues.append({
                'rule': 'Page must have lang attribute',
                'impact': 'serious',
                'count': 1,
                'description': 'HTML element missing lang attribute'
            })
        else:
            self.passes.append(f'Page language set to: {html.get("lang")}')

    def _check_page_title(self, soup):
        """Check if page has a title."""
        title = soup.find('title')
        if not title or not title.get_text(strip=True):
            self.issues.append({
                'rule': 'Page must have a title',
                'impact': 'serious',
                'count': 1,
                'description': 'No page title found'
            })
        else:
            self.passes.append(f'Page title: "{title.get_text(strip=True)}"')

    def _check_landmarks(self, soup):
        """Check for ARIA landmarks."""
        has_main = soup.find(['main', '[role="main"]'])
        has_nav = soup.find(['nav', '[role="navigation"]'])

        if not has_main:
            self.warnings.append({
                'rule': 'Page should have main landmark',
                'impact': 'moderate',
                'count': 1,
                'description': 'No <main> or role="main" found'
            })

        if not has_nav:
            self.warnings.append({
                'rule': 'Page should have navigation landmark',
                'impact': 'minor',
                'count': 1,
                'description': 'No <nav> or role="navigation" found'
            })

    def _check_buttons(self, soup):
        """Check buttons for accessible names."""
        buttons = soup.find_all('button')
        buttons_without_text = [
            btn for btn in buttons
            if not btn.get_text(strip=True) and not btn.get('aria-label')
        ]

        if buttons_without_text:
            self.issues.append({
                'rule': 'Buttons must have accessible names',
                'impact': 'critical',
                'count': len(buttons_without_text),
                'description': f'{len(buttons_without_text)} buttons have no text or label'
            })

    def _display_results(self):
        """Display the results."""
        print("\n" + "=" * 70)
        print("📊 ACCESSIBILITY CHECK RESULTS")
        print("=" * 70)

        total_issues = len(self.issues)
        total_warnings = len(self.warnings)
        total_passes = len(self.passes)

        # Summary
        print(f"\n✅ Passes: {total_passes}")
        print(f"⚠️  Warnings: {total_warnings}")
        print(f"❌ Issues: {total_issues}")

        # Issues (Critical/Serious)
        if self.issues:
            print("\n" + "=" * 70)
            print("❌ ISSUES FOUND (Must Fix)")
            print("=" * 70)
            for issue in self.issues:
                print(f"\n[{issue['impact'].upper()}] {issue['rule']}")
                print(f"   {issue['description']}")

        # Warnings
        if self.warnings:
            print("\n" + "=" * 70)
            print("⚠️  WARNINGS (Should Fix)")
            print("=" * 70)
            for warning in self.warnings:
                print(f"\n[{warning['impact'].upper()}] {warning['rule']}")
                print(f"   {warning['description']}")

        # Passes
        if self.passes:
            print("\n" + "=" * 70)
            print("✅ PASSED CHECKS")
            print("=" * 70)
            for check in self.passes:
                print(f"   ✓ {check}")

        # Final summary
        print("\n" + "=" * 70)
        if total_issues == 0:
            print("🎉 No critical issues found!")
        else:
            print(f"⚠️  Found {total_issues} issues that need to be fixed")
        print("=" * 70)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python check_static.py <URL>")
        print("Example: python check_static.py https://example.com")
        sys.exit(1)

    url = sys.argv[1]
    if not url.startswith('http'):
        url = 'https://' + url

    checker = StaticAccessibilityChecker(url)
    checker.check()

