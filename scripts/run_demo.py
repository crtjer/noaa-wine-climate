#!/usr/bin/env python3
"""Standalone demo runner — runs the pipeline in demo mode."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.argv = ["run_demo", "--demo"]

from pipeline.metrics import main
main()
