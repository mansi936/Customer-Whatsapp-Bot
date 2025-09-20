# E-Commerce WhatsApp Bot with MCP Architecture

An AI-powered WhatsApp shopping assistant that enables customers to browse products, manage carts, place orders, and even try on clothes virtually - all through WhatsApp conversations.

## 🌟 Features

### Core Shopping Features
- **Product Search & Discovery**: Natural language product search with filters
- **Smart Recommendations**: AI-powered personalized product suggestions
- **Cart Management**: Add, view, and manage shopping cart via chat
- **Order Processing**: Complete checkout flow within WhatsApp
- **Order Tracking**: Real-time order status updates

### Advanced Features
- **Virtual Try-On**: Upload your photo and see how clothes look on you
- **Multi-language Support**: Communicate in your preferred language
- **Image-based Search**: Send product images to find similar items
- **Price Alerts**: Get notified when prices drop on saved items

## 🏗️ Architecture

### MCP (Model Context Protocol) Design
The bot uses a client-server architecture with MCP for tool execution:

```
WhatsApp User
    ↓
EnableX Webhook (FastAPI)
    ↓
MCP Client Pool → LLM Service (Azure OpenAI)
    ↓
MCP Server (Tools)
    ↓
Services (Redis, MongoDB, Azure Storage, etc.)
```

### Key Components

1. **Webhook Handler** (`webhook/enablex_webhook.py`)
   - Receives WhatsApp messages via EnableX
   - Manages async message processing
   - Handles media uploads

2. **MCP Client** (`client/mcp_client.py`)
   - Connects to MCP server via STDIO
   - Manages conversation context
   - Formats responses for WhatsApp

3. **MCP Server** (`server/mcp_server.py`)
   - Provides e-commerce tools/functions
   - Handles product operations
   - Manages virtual try-on

4. **Service Layer**
   - **LLM Service**: Azure OpenAI integration
   - **Redis**: Session management and caching
   - **MongoDB**: User profiles and preferences
   - **Azure Storage**: Image storage for try-ons
   - **EnableX**: WhatsApp messaging API

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Redis server
- MongoDB (optional)
- Azure account (for OpenAI and Storage)
- EnableX account with WhatsApp Business API

### Installation

1. **Clone and setup virtual environment**
```bash
git clone <repository>
cd ecommerce-bot
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure environment variables**
Create a `.env` file with:
```env
# Azure OpenAI
AZURE_OPENAI_API_KEY=your_key
AZURE_OPENAI_ENDPOINT=your_endpoint
AZURE_OPENAI_DEPLOYMENT=gpt-4

# Azure Storage (optional for images)
AZURE_STORAGE_CONNECTION_STRING=your_connection_string

# EnableX WhatsApp
ENABLEX_APP_ID=your_app_id
ENABLEX_APP_KEY=your_app_key
ENABLEX_WHATSAPP_NUMBER=your_whatsapp_number

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# MongoDB (optional)
MONGODB_URI=mongodb://localhost:27017/

# Gemini API (optional for try-on)
GEMINI_API_KEY=your_gemini_key
```

### Running the Bot

**Development Mode (with auto-reload)**
```bash
uvicorn webhook.enablex_webhook:app --host 0.0.0.0 --port 8000 --reload
```

**Production Mode**
```bash
python webhook/enablex_webhook.py
```

### Testing

1. **Configure EnableX Webhook**
   - Set webhook URL: `https://your-domain.com/enablex/whatsapp/webhook`
   - Or use ngrok for local testing: `ngrok http 8000`

2. **Send a test message**
   - Message your WhatsApp Business number
   - Try: "Hi", "Show me laptops", "Add to cart", etc.

## 📱 Usage Examples

### Basic Shopping Flow
```
User: Hi
Bot: Hello! 👋 Welcome to our store! How can I help you shop today?

User: I'm looking for a laptop under 60000
Bot: I'll help you find the perfect laptop within your budget! Let me search...
[Shows laptop options with prices]

User: Add the HP Pavilion to my cart
Bot: ✅ Added HP Pavilion to your cart!
[Shows cart summary]

User: Checkout
Bot: Let's complete your order! I'll need your delivery details...
```

### Virtual Try-On
```
User: Can I try on that blue shirt?
Bot: Yes! Our virtual try-on feature lets you see how it looks on you. 
Please send a photo of yourself (full body works best).

User: [Sends photo]
Bot: Perfect! Processing your virtual try-on...
[Returns image with user wearing the blue shirt]
```

## 🔧 Development

### Project Structure
```
ecommerce-bot/
├── webhook/              # FastAPI webhook handler
├── client/              # MCP client and connection pool
├── server/              # MCP server with e-commerce tools
├── services/            # Service integrations
│   ├── llm/            # LLM service with fallbacks
│   ├── redis/          # Session management
│   ├── mongodb/        # User data
│   ├── tryon/          # Virtual try-on
│   └── image_service.py # Image handling
├── tests/              # Test suite
└── examples/           # Usage examples
```

### Adding New Tools
1. Add tool function to `server/mcp_server.py`:
```python
@mcp.tool()
async def your_tool(param1: str, param2: int) -> str:
    """Tool description for LLM"""
    # Implementation
    return result
```

2. Update prompts in `client/prompts.py` if needed

### Extending the Bot
- **New LLM Providers**: Add to `services/llm/unified_llm_service.py`
- **Custom Workflows**: Modify conversation flows in `client/prompts.py`
- **New Services**: Add to `services/` and initialize in webhook

## 🧪 Testing

Run the test suite:
```bash
pytest tests/
```

Test specific components:
```bash
# Test MCP connection
python test_mcp_server_direct.py

# Test LLM service
python test_integration.py

# Test webhook
python test_webhook.py
```

## 🚢 Deployment

### Docker
```bash
docker build -t ecommerce-bot .
docker run -p 8000:8000 --env-file .env ecommerce-bot
```

### Kubernetes
```bash
kubectl apply -f kubernetes/deployment.yaml
```

See `PRODUCTION_DEPLOYMENT.md` for detailed deployment instructions.

## 🔐 Security Considerations

- Store API keys in environment variables
- Enable webhook signature verification
- Use HTTPS for all endpoints
- Implement rate limiting
- Validate and sanitize user inputs
- Regular security audits

## 📊 Monitoring

The bot includes built-in monitoring:
- Health check endpoint: `/health`
- Prometheus metrics (optional)
- Structured logging with correlation IDs
- Error tracking and alerting

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

[Your License Here]

## 🆘 Support

- Documentation: See `/docs` folder
- Issues: GitHub Issues
- Email: support@example.com

## 🚦 Status

- ✅ Core shopping features
- ✅ MCP integration
- ✅ Multi-provider LLM support
- ✅ Virtual try-on (requires Gemini API)
- 🚧 Advanced analytics
- 🚧 Multi-language support

