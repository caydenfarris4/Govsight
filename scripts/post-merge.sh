#!/bin/bash
set -e

# Install Node.js dependencies for the Budget Playground API
if [ -f "budget_playground_api/package.json" ]; then
    echo "Installing Budget Playground API dependencies..."
    cd budget_playground_api && npm install --yes 2>&1 && cd ..
fi

echo "Post-merge setup complete."
