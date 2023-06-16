# Discord hangman bot

This program acts as a server backend, so one instance of it on a server could handle many, many games on many, many discord servers. It communicates with the Discord Gateway API (https://discord.com/developers/docs/intro) to run a hangman discord bot, using the pycord python library (https://docs.pycord.dev/en/stable/). The bot, when in a discord server, allows users to play hangman, with highly configurable gamemodes (not quite yet).

## Getting started
You need Python >3.11 (iirc), as well as the pycord library:
```
$ py -m pip install py-cord
```
You can optionally use the `py-cord[speed]` package for better performance:
```
$ py -m pip install py-cord[speed]
```

To run bot, just run the `main.py` file:
```
$ py main.py
```
This will start the discord bot. You will need a bot token, so if the program crashes immediately this is probably why. In `config.txt`, replace the `<TOKEN>` after `discord_token=` with your bot's discord token, and run the script again.
