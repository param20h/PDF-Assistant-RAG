# Discord RAG Bot

This bot connects to the PDF-Assistant-RAG backend to answer questions based on your uploaded documents, directly from Discord.

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Create a Discord Bot on the [Discord Developer Portal](https://discord.com/developers/applications):
   - Go to "Bot" tab and enable **Message Content Intent**.
   - Copy the bot token.
   - Invite the bot to your server via the OAuth2 URL Generator (check `bot` scope and `Send Messages` permission).

3. Generate an API Key from your PDF-Assistant-RAG profile dashboard.

4. Set the environment variables and run:
   ```bash
   export DISCORD_TOKEN="your-discord-bot-token"
   export RAG_API_KEY="rag_your-api-key"
   
   # Optional: set API_URL if backend is not running on localhost:8000
   # export API_URL="http://localhost:8000/api/v1"
   
   python bot.py
   ```

## Usage
In a Discord channel where the bot is present, simply use the `!ask` command:

```
!ask Summarize the latest uploaded report for me
```

The bot will query the backend API using your personal API key and reply with the generated answer.
