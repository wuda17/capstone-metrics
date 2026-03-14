#!/usr/bin/env bash
set -euo pipefail

echo "Start each command in a separate terminal:"
echo "  1) python -m localhost_demo.services.metrics_service"
echo "  2) python -m localhost_demo.services.aggregator"
echo "  3) streamlit run localhost_demo/dashboard/app.py"
echo ""
echo "Drop WAV files into localhost_demo/data/incoming/"
