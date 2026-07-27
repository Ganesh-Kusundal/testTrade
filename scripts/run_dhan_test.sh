#!/bin/bash
# Setup Dhan credentials and run connection tests
#
# Usage:
#   ./scripts/run_dhan_test.sh [--sandbox]
#   ./scripts/run_dhan_test.sh --client-id YOUR_ID --access-token YOUR_TOKEN

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║${NC}  ${GREEN}Dhan Connection & Endpoint Tester${NC}                        ${BLUE}║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

# Parse arguments
SANDBOX=""
CLIENT_ID=""
ACCESS_TOKEN=""
VERBOSE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --sandbox)
            SANDBOX="--sandbox"
            shift
            ;;
        --client-id)
            CLIENT_ID="$2"
            shift 2
            ;;
        --access-token)
            ACCESS_TOKEN="$2"
            shift 2
            ;;
        --verbose|-v)
            VERBOSE="--verbose"
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --sandbox              Use sandbox environment"
            echo "  --client-id ID         Dhan client ID"
            echo "  --access-token TOKEN   Dhan access token"
            echo "  --verbose, -v          Verbose output"
            echo "  --help, -h             Show this help"
            echo ""
            echo "Environment Variables:"
            echo "  DHAN_CLIENT_ID         Dhan client ID"
            echo "  DHAN_ACCESS_TOKEN      Dhan access token"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Check if credentials are available
if [ -z "$CLIENT_ID" ]; then
    CLIENT_ID="${DHAN_CLIENT_ID:-}"
fi

if [ -z "$ACCESS_TOKEN" ]; then
    ACCESS_TOKEN="${DHAN_ACCESS_TOKEN:-}"
fi

if [ -z "$CLIENT_ID" ] || [ -z "$ACCESS_TOKEN" ]; then
    echo -e "${YELLOW}⚠️  No credentials found!${NC}"
    echo ""
    echo "Please provide credentials in one of these ways:"
    echo ""
    echo "1. Environment variables:"
    echo -e "   ${GREEN}export DHAN_CLIENT_ID='your_client_id'${NC}"
    echo -e "   ${GREEN}export DHAN_ACCESS_TOKEN='your_access_token'${NC}"
    echo ""
    echo "2. Command-line arguments:"
    echo -e "   ${GREEN}$0 --client-id YOUR_ID --access-token YOUR_TOKEN${NC}"
    echo ""
    echo "3. Create a .env file (auto-loaded):"
    echo -e "   ${GREEN}echo 'DHAN_CLIENT_ID=your_id' > .env${NC}"
    echo -e "   ${GREEN}echo 'DHAN_ACCESS_TOKEN=your_token' >> .env${NC}"
    echo ""
    
    # Try to load from .env file if it exists
    if [ -f "$PROJECT_DIR/.env" ]; then
        echo -e "${BLUE}📄 Loading credentials from .env file...${NC}"
        export $(grep -v '^#' "$PROJECT_DIR/.env" | xargs)
        CLIENT_ID="${DHAN_CLIENT_ID:-}"
        ACCESS_TOKEN="${DHAN_ACCESS_TOKEN:-}"
        
        if [ -n "$CLIENT_ID" ] && [ -n "$ACCESS_TOKEN" ]; then
            echo -e "${GREEN}✅ Credentials loaded from .env${NC}"
            echo ""
        else
            echo -e "${RED}❌ .env file exists but missing credentials${NC}"
            exit 1
        fi
    else
        exit 1
    fi
fi

# Mask token for display
MASKED_TOKEN="${ACCESS_TOKEN:0:10}...${ACCESS_TOKEN: -5}"

echo -e "${BLUE}📋 Configuration:${NC}"
echo -e "   Client ID: ${GREEN}${CLIENT_ID}${NC}"
echo -e "   Access Token: ${GREEN}${MASKED_TOKEN}${NC}"

if [ -n "$SANDBOX" ]; then
    echo -e "   Environment: ${YELLOW}SANDBOX${NC}"
else
    echo -e "   Environment: ${GREEN}LIVE${NC}"
fi

echo ""

# Run the test
echo -e "${BLUE}🚀 Running Dhan endpoint tests...${NC}"
echo ""

cd "$PROJECT_DIR"
python scripts/test_dhan_connection.py \
    --client-id "$CLIENT_ID" \
    --access-token "$ACCESS_TOKEN" \
    $SANDBOX \
    $VERBOSE

EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✅ All tests passed!${NC}"
else
    echo -e "${RED}❌ Some tests failed. Check the logs above.${NC}"
fi

exit $EXIT_CODE
