#!/bin/bash

# Set the PYTHONPATH to include the project root directory
export PYTHONPATH=$(pwd):$PYTHONPATH

# Run the tests
python run_tests.py