#!/bin/bash

# Hugo CMS Local Development Script
# This script helps you run the Hugo CMS locally using Docker

set -e

IMAGE_NAME="hugo-cms"
CONTAINER_NAME="hugo-cms-dev"

echo "🔧 Building Docker image..."
docker build -t $IMAGE_NAME .

echo "🧹 Stopping any existing container..."
docker stop $CONTAINER_NAME 2>/dev/null || true
docker rm $CONTAINER_NAME 2>/dev/null || true

echo "🚀 Starting Hugo CMS container..."
docker run -d \
  --name $CONTAINER_NAME \
  -p 5000:5000 \
  -e GIT_PYTHON_REFRESH=quiet \
  -e FLASK_ENV=development \
  -e FLASK_DEBUG=1 \
  -v hugo_cms_data:/tmp/hugo-cms-work \
  $IMAGE_NAME

echo "✅ Hugo CMS is running!"
echo "📱 Access it at: http://localhost:5000"
echo ""
echo "📋 Useful commands:"
echo "  View logs: docker logs -f $CONTAINER_NAME"
echo "  Stop:      docker stop $CONTAINER_NAME"
echo "  Remove:    docker rm $CONTAINER_NAME"
echo ""

# Show logs for a few seconds
sleep 2
echo "📄 Recent logs:"
docker logs --tail 10 $CONTAINER_NAME
