#!/bin/bash
set -e

# Authenticate to the Thought Machine wheel index
echo "🔐 Authenticating to Thought Machine Artifact Registry..."

# Pre-verify GitHub SSH to prevent hangs
if [[ -z "$(ssh-keygen -F github.com 2>/dev/null)" ]]; then
    echo "🌐 Adding github.com to known_hosts to prevent SSH hangs..."
    mkdir -p ~/.ssh
    ssh-keyscan -H github.com >> ~/.ssh/known_hosts 2>/dev/null
fi

# Ensure SSH agent is running and has a key loaded
if ! ssh-add -l >/dev/null 2>&1; then
    echo "🔑 No SSH keys loaded. Starting ssh-agent and adding keys..."
    eval "$(ssh-agent -s)"
    ssh-add
fi

# Run cloud-auth if it's available
if command -v cloud-auth &> /dev/null; then
    cloud-auth -t api -r cloudops tm-gcp-dh-clusters-0
else
    echo "⚠️  Warning: 'cloud-auth' not found. Ensure you are authenticated manually."
fi

# Set UV credentials using gcloud token
if command -v gcloud &> /dev/null; then
    TOKEN=$(gcloud auth print-access-token)
    export UV_INDEX_TM_WHEELS_USERNAME="oauth2accesstoken"
    export UV_INDEX_TM_WHEELS_PASSWORD="$TOKEN"
    export UV_INDEX_TM_BINARIES_USERNAME="oauth2accesstoken"
    export UV_INDEX_TM_BINARIES_PASSWORD="$TOKEN"
    echo "✅ Credentials exported for UV."
else
    echo "❌ Error: 'gcloud' not found. Please install Google Cloud SDK."
    return 1
fi

set +e

# To use these in the current shell, you must 'source' this script.
# However, for 'make setup', we will pass these directly to uv.
