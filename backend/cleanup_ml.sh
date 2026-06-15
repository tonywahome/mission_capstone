#!/bin/bash
# TerraFoma Project Cleanup Script
# Removes temporary and test files

echo "🧹 Cleaning up TerraFoma ML directory..."
echo ""

cd ml

# Count files before
BEFORE=$(ls -1 | wc -l | tr -d ' ')

# Remove temporary documentation
echo "Removing temporary documentation files..."
rm -f GEDI_TROUBLESHOOTING.md
rm -f QUESTIONS_ANSWERED.md
rm -f QUICKSTART_NOW.md
rm -f data_collection_guide.md

# Remove test scripts
echo "Removing test/debug scripts..."
rm -f example_quickstart.py
rm -f find_gedi_products.py
rm -f test_gedi_regions.py
rm -f test_simple_gedi.py

# Remove redundant files
echo "Removing redundant files..."
rm -f quickstart.sh
rm -f requirements_optional.txt
rm -f train_model.py

# Count files after
AFTER=$(ls -1 | wc -l | tr -d ' ')
REMOVED=$((BEFORE - AFTER))

echo ""
echo "✅ Cleanup complete!"
echo "   Removed: $REMOVED files"
echo "   Remaining: $AFTER files"
echo ""
echo "Essential files kept:"
echo "  ✓ collect_gedi_data.py"
echo "  ✓ collect_sentinel_data.py"
echo "  ✓ train_real_model.py"
echo "  ✓ generate_synthetic_data.py"
echo "  ✓ README.md"
echo "  ✓ requirements_data_collection.txt"
echo "  ✓ Model files (*.pkl)"
echo "  ✓ GEDI data (gedi_data/*.h5)"
echo ""
