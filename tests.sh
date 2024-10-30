#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo "Starting local test suite..."

# Start the services
echo "Starting services..."
docker-compose up -d

# Wait for service to be ready
echo "Waiting for service to be ready..."
sleep 5

# Test health endpoint
echo -e "\n${GREEN}Testing health endpoint:${NC}"
curl -s http://localhost:8000/health | jq .

# Test validation endpoint
echo -e "\n${GREEN}Testing validation endpoint:${NC}"
curl -s -X POST \
  http://localhost:8000/validate \
  -H 'Content-Type: application/json' \
  -d '{
    "spreadsheet_id": "1niDCOegC7SKkqYjCDhKkia3Oc6D-5bvUIHKDnNMG8YE",
    "range_name": "store_id_level_matched!A:Z",
    "max_pdfs": 2
  }' | jq .

# Show logs if there are errors
if [ $? -ne 0 ]; then
    echo -e "\n${RED}Error detected. Showing logs:${NC}"
    docker-compose logs
fi

# Option to stop services
read -p "Do you want to stop the services? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
    docker-compose down
fi