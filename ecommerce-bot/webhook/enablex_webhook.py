from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import uvicorn

app = FastAPI(title="EnableX Webhook Handler")

@app.post("/webhook/enablex")
async def enablex_webhook(request: Request):
    payload = await request.json()
    # TODO: validate signature, parse message types (text/media), initialize or retrieve session
    # Forward to MCP client for processing
    return JSONResponse({"status": "received", "payload_summary": str(list(payload.keys())[:5])})

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
