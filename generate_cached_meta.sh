#!/bin/bash
# generate_cached_meta.sh
# Generate meta images and cache them to the repository for faster CI builds

set -e

echo "🎨 Generating meta images with caching enabled..."
echo "This will generate all meta images and save them to meta_images/ directory"
echo ""

# Generate to a temporary output directory and cache the meta images
python3 generate_verifications.py --out ./dist --clean --cache-meta

echo ""
echo "✅ Meta images have been cached to meta_images/"
echo "💡 You can now commit these cached images to speed up CI builds:"
echo ""
echo "   git add meta_images/"
echo "   git commit -m 'chore: cache meta images'"
echo "   git push"
echo ""
echo "🚀 Future CI builds will use cached images when available!"
