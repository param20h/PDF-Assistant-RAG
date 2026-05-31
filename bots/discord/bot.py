import os
import discord
import requests
from discord.ext import commands

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
API_URL = os.getenv("API_URL", "http://localhost:8000/api/v1")
RAG_API_KEY = os.getenv("RAG_API_KEY")

if not DISCORD_TOKEN or not RAG_API_KEY:
    print("Error: DISCORD_TOKEN and RAG_API_KEY must be set in environment variables.")
    exit(1)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name} ({bot.user.id})")
    print("Ready to answer questions via '!ask <question>'")

@bot.command(name="ask")
async def ask_rag(ctx, *, question: str):
    """Ask the RAG Assistant a question. Example: !ask What is in my documents?"""
    loading_msg = await ctx.send("🤔 Thinking...")
    
    try:
        headers = {
            "Authorization": f"Bearer {RAG_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # We can also support document_id if we want, but for now we do global ask.
        payload = {"question": question}
        
        response = requests.post(
            f"{API_URL}/chat/ask",
            json=payload,
            headers=headers,
            timeout=30  # Give the RAG backend some time to process
        )
        
        if response.status_code == 200:
            data = response.json()
            answer = data.get("answer", "No answer provided.")
            
            if len(answer) > 2000:
                # Discord has a 2000 character limit per message
                chunks = [answer[i:i+2000] for i in range(0, len(answer), 2000)]
                await loading_msg.edit(content=chunks[0])
                for chunk in chunks[1:]:
                    await ctx.send(chunk)
            else:
                await loading_msg.edit(content=answer)
        else:
            await loading_msg.edit(content=f"⚠️ Error from RAG API: `{response.status_code}`")
            print(f"API Error: {response.text}")
            
    except requests.exceptions.RequestException as e:
        await loading_msg.edit(content=f"❌ Failed to connect to backend API.")
        print(f"Request Error: {e}")
    except Exception as e:
        await loading_msg.edit(content=f"❌ An unexpected error occurred.")
        print(f"Error: {e}")

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
