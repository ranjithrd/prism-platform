#!/bin/bash

# Define the schema URL
SCHEMA_URL="http://localhost:8000/openapi.json"
OUTPUT_FILE="./openapi.json"

echo "⏳  Fetching OpenAPI schema from $SCHEMA_URL..."

# Use curl to fetch the schema
# -sS: Silent mode but show errors
# -o: Output file
curl -sS -o $OUTPUT_FILE $SCHEMA_URL

# Check if curl command failed
if [ $? -ne 0 ]; then
  echo "❌  Failed to fetch schema. Is the server running at http://localhost:8000?"
  exit 1
fi

echo "✅  Schema downloaded successfully to $OUTPUT_FILE"
echo "⏳  Generating API client with Orval..."

# Run Orval
npx orval

# Check if orval command failed
if [ $? -ne 0 ]; then
  echo "❌  Orval failed to generate the client."
  exit 1
fi

echo "🎉  API client generated successfully!"