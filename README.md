# Spoiler-chan
Discord bot to detect text spoilers and mark mobile spoilers.

## Installation
1. Clone the repository
2. Run `pip install -r requirements.txt` inside the repository
3. Run the bot using `python spoilerchan/spoilerchan.py`

### .env
The following variables should be placed in a `.env` file:

```
DISCORD_TOKEN=<Replace this with the bot token>
```

## Commands
### Everyone
- `s!tag Text warning to go with your spoiler` - Uploads the image attachment for the message as a spoiler (useful for mobile)

### Mods
- `s!spoiler add Spoiler Series` - Adds a new spoiler to watch for
