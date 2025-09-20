# EnableX WhatsApp Webhook

This webhook handles incoming WhatsApp messages via EnableX and processes them using the MCP client.

## Features

- **Message Handling**: Processes text and media messages from WhatsApp
- **Media Support**: Downloads and uploads images to Azure storage
- **Session Management**: Maintains user sessions in Redis
- **Background Processing**: Processes messages asynchronously
- **Health Check**: Provides endpoint to monitor service status

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables (copy `.env.example` to `.env` and fill in values):
```bash
cp .env.example .env
```

3. Run the webhook server:
```bash
python webhook/enablex_webhook.py
```

The server will start on `http://localhost:8000`

## Endpoints

- `POST /enablex/whatsapp/webhook` - Main webhook endpoint for EnableX
- `GET /health` - Health check endpoint

## Message Flow

1. EnableX sends webhook request with WhatsApp message
2. Webhook extracts message content and media
3. Media files are downloaded and uploaded to Azure storage
4. Message is processed by MCP client
5. Response is sent back via EnableX WhatsApp API

## Configuration

Required environment variables:
- `ENABLEX_APP_ID` - Your EnableX App ID
- `ENABLEX_APP_KEY` - Your EnableX App Key  
- `ENABLEX_WHATSAPP_NUMBER` - Your WhatsApp business number
- `MONGODB_URI` - MongoDB connection string
- `AZURE_STORAGE_CONNECTION_STRING` - For image storage

## Testing

You can test the webhook locally using ngrok:

```bash
ngrok http 8000
```

Then configure the ngrok URL in your EnableX WhatsApp webhook settings.