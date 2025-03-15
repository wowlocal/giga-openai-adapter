#!/usr/bin/env python3
import os
import sys
import unittest

# Add the project root directory to the Python path
# This ensures that the 'app' module can be imported correctly
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def run_tests():
    """Run all tests in the tests directory."""
    # Discover and run tests
    test_loader = unittest.TestLoader()
    test_suite = test_loader.discover('tests', pattern='test_*.py')

    # Run the tests
    test_runner = unittest.TextTestRunner(verbosity=2)
    result = test_runner.run(test_suite)

    # Return appropriate exit code
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(run_tests())