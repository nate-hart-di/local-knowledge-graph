#!/bin/bash

# N8N Credential Injection Methods
# Different ways to inject credentials into n8n on startup

echo "N8N Credential Injection Methods"
echo "================================="

# Method 1: Environment Variables (add to docker-compose.yml)
cat << 'EOF'

## Method 1: Environment Variables in Docker Compose
Add to your n8n service environment section:

```yaml
n8n:
  environment:
    # ... existing vars ...
    # OpenAI Credentials
    N8N_OPENAI_API_KEY: ${OPENAI_API_KEY}
    # Google Credentials  
    N8N_GOOGLE_CLIENT_ID: ${GOOGLE_CLIENT_ID}
    N8N_GOOGLE_CLIENT_SECRET: ${GOOGLE_CLIENT_SECRET}
    # Slack Credentials
    N8N_SLACK_BOT_TOKEN: ${SLACK_BOT_TOKEN}
    # Database connections
    N8N_DB_POSTGRES_HOST: ${POSTGRES_HOST}
    N8N_DB_POSTGRES_USER: ${POSTGRES_USER}
    N8N_DB_POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
```

Then n8n can access these as: process.env.N8N_OPENAI_API_KEY

EOF

# Method 2: Init Container with Credential Creation
cat << 'EOF'

## Method 2: Init Container that Creates Credentials via API
Create an init container that uses n8n's API to create credentials:

```yaml
n8n-credential-setup:
  image: curlimages/curl:latest
  depends_on:
    n8n:
      condition: service_healthy
  command:
    - /bin/sh
    - -c
    - |
      echo "Waiting for n8n to be ready..."
      sleep 10
      
      # Create OpenAI credential
      curl -X POST http://n8n:5678/rest/credentials \
        -H "Content-Type: application/json" \
        -d '{
          "name": "OpenAI",
          "type": "openAiApi", 
          "data": {
            "apiKey": "'${OPENAI_API_KEY}'"
          }
        }'
      
      # Create more credentials as needed...
```

EOF

# Method 3: Volume Mount Pre-created Credentials
cat << 'EOF'

## Method 3: Pre-created Credential Files
Export credentials once, then mount them:

1. Export credentials from working n8n:
   ```bash
   docker exec n8n n8n export:credentials --output=/tmp/creds --separate
   ```

2. Mount the credential files:
   ```yaml
   n8n:
     volumes:
       - ./n8n/credentials:/home/node/.n8n/credentials:ro
   ```

EOF

# Method 4: Custom Init Script
cat << 'EOF'

## Method 4: Custom Initialization Script
Create a custom entrypoint that sets up credentials:

```dockerfile
# Custom n8n image with credential setup
FROM n8nio/n8n:latest

COPY init-credentials.sh /init-credentials.sh
RUN chmod +x /init-credentials.sh

ENTRYPOINT ["/init-credentials.sh"]
```

init-credentials.sh:
```bash
#!/bin/bash
# Set up credentials from environment variables
n8n credentials:create openai --data='{"apiKey":"'$OPENAI_API_KEY'"}'
n8n credentials:create postgres --data='{"host":"'$POSTGRES_HOST'","user":"'$POSTGRES_USER'","password":"'$POSTGRES_PASSWORD'"}'

# Start n8n normally
exec n8n start
```

EOF

echo ""
echo "Which method would you like me to implement for your setup?"
echo "1. Environment variables (easiest)"
echo "2. API-based credential injection (most flexible)"
echo "3. Pre-created credential files (most reliable)"
echo "4. Custom init script (most control)"
