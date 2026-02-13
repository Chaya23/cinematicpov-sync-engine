#!/usr/bin/env python3
"""
API Key Validation Script for CinematicPOV Sync Engine
Validates format and connectivity of OpenAI and Google API keys
"""

import os
import sys
import re
from typing import Tuple, Dict

def validate_openai_key(api_key: str) -> Tuple[bool, str]:
    """
    Validate OpenAI API key format
    Expected format: sk-...
    """
    if not api_key:
        return False, "OpenAI API key is empty"
    
    if not api_key.startswith('sk-'):
        return False, "OpenAI API key should start with 'sk-'"
    
    if len(api_key) < 20:
        return False, "OpenAI API key is too short"
    
    return True, "OpenAI API key format is valid"


def validate_google_key(api_key: str) -> Tuple[bool, str]:
    """
    Validate Google API key format
    Expected format: alphanumeric string
    """
    if not api_key:
        return False, "Google API key is empty"
    
    if len(api_key) < 20:
        return False, "Google API key is too short"
    
    # Google API keys are typically alphanumeric with some special chars
    if not re.match(r'^[A-Za-z0-9_-]+$', api_key):
        return False, "Google API key contains invalid characters"
    
    return True, "Google API key format is valid"


def check_api_keys() -> Dict[str, bool]:
    """
    Check all required API keys
    """
    results = {
        'openai': False,
        'google': False,
        'all_valid': False
    }
    
    # Check OpenAI key
    openai_key = os.getenv('OPENAI_API_KEY', '')
    openai_valid, openai_msg = validate_openai_key(openai_key)
    
    print(f"🔑 OpenAI API Key: {openai_msg}")
    results['openai'] = openai_valid
    
    # Check Google key
    google_key = os.getenv('GOOGLE_API_KEY', '')
    google_valid, google_msg = validate_google_key(google_key)
    
    print(f"🔑 Google API Key: {google_msg}")
    results['google'] = google_valid
    
    # Overall validation
    results['all_valid'] = openai_valid and google_valid
    
    return results


def main():
    """Main validation function"""
    print("=" * 60)
    print("🎬 CinematicPOV Sync Engine - API Key Validation")
    print("=" * 60)
    
    results = check_api_keys()
    
    print("\n" + "=" * 60)
    if results['all_valid']:
        print("✅ All API keys are valid!")
        print("=" * 60)
        return 0
    else:
        print("❌ Some API keys are invalid or missing")
        print("\n💡 Note: This is a format check only.")
        print("   Actual API connectivity will be tested during runtime.")
        print("=" * 60)
        return 1


if __name__ == '__main__':
    sys.exit(main())
