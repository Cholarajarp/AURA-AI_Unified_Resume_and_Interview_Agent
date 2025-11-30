#!/usr/bin/env bash
set -euo pipefail

echo "======================================"
echo "Building and copying frontend assets"
echo "======================================"

# 1) Build frontend
echo "Building frontend..."
if [ -f frontend/package.json ]; then
  npm ci --prefix frontend
  npm run build --prefix frontend
  echo "✓ Frontend built successfully"
else
  echo "✗ No frontend/package.json found"
  exit 1
fi

# 2) Copy build artifacts to backend
echo "Copying build artifacts to backend..."
mkdir -p backend/templates backend/static

if [ -d frontend/dist ]; then
  echo "Found frontend/dist (Vite output)"
  cp frontend/dist/index.html backend/templates/index.html
  cp -r frontend/dist/* backend/static/
  echo "✓ Copied frontend/dist -> backend/{templates,static}"
elif [ -d frontend/build ]; then
  echo "Found frontend/build (Create React App output)"
  cp frontend/build/index.html backend/templates/index.html
  cp -r frontend/build/* backend/static/
  echo "✓ Copied frontend/build -> backend/{templates,static}"
else
  echo "✗ No build output found in frontend/dist or frontend/build"
  exit 1
fi

echo "======================================"
echo "✓ Build and copy completed!"
echo "======================================"
echo ""
echo "Next steps:"
echo "  1. git add backend/templates backend/static"
echo "  2. git commit -m 'Add frontend build artifacts'"
echo "  3. git push origin main"
echo ""
echo "To test locally:"
echo "  uvicorn backend.main:app --reload --port 8000"
echo "  then visit http://localhost:8000"
