# Jingler
![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-blue?style=flat-square)
![Version](https://img.shields.io/badge/jingler-1.0.1-orange?style=flat-square)

A Discord bot for spicing up your voice channel entry with random jingles, 
custom member "theme songs" and more.

## 1. About
Jingler is a Discord bot for playing short audio clips (also called [jingles](https://www.merriam-webster.com/dictionary/jingle)) in voice channels.

Jingler maintains a global list of available jingles. Each user can search them and upload their own short jingles, which will in turn also become available
to every other user. By default, Jingler will play a random jingle each time a member joins a voice channel.

To spice things up, each user can set their own favourite jingle - a "theme song" of sorts. If a user has a theme song, it will be played each time they
enter a voice channel. Theme songs override the jingle mode on each server unless their theme song mode is set to `disable` (see below for server configuration).

You can control jingle behaviour per-server:
- Jingle mode: you can disable all automatic jingles (`disabled` mode; manually playing them with `.playrandom` is still possible), 
  set a specific jingle for your server (`single` mode) or configure Jingler to always play a random, fresh jingle (`random` mode; best option 😉 ).
- Theme song mode: theme songs are user-specific and (by default) override the server jingle mode if a user has one. If you wish to ignore personal theme songs instead and want to
  force the jingle mode you set for your server, set the theme song mode to `disabled`.

## 2. Commands

### Jingles
| Command        | Usage | Description                                                                                                                   |
|----------------|-------|-------------------------------------------------------------------------------------------------------------------------------|
| .playrandom    |   /   | Manually play a random jingle in your current voice channel.                                                                  |
| .listjingles   |   /   | Interactively browse all available jingles. React with appropriate arrows below the message to browse different pages.        |
| .addjingle     |   /   | Interactively add a new jingle. Give it a title and upload the .mp3 file. Note: MP3 files are limited to 1 MB and 10 seconds. |
| .reloadjingles |   /   | Reload available jingles. This is generally unnecessary.                                                                      |

### Server settings
|   Command         |           Usage            |                                                                                                                                                            Description                                                                                                                                                           |
|-------------------|----------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| .getdefault       |             /              | Displays the default jingle for this server.                                                                                                                                                                                                                                                                                     |
| .setdefault       | (jingle code)              | Sets the default jingle for this server. If the server jingle mode isn't set to "single", this will have no effect.                                                                                                                                                                                                              |
| .getjinglemode    |             /              | Displays the jingle mode for the current server.                                                                                                                                                                                                                                                                                 |
| .setjinglemode    | [disabled/single/random]   | Sets the jingle mode for the current server. Available modes dictate behaviour upon members joining a voice channel:<br><br> **disabled** - do not play any jingles<br> **single** - play a specific jingle (personal theme songs override this)<br> **random** - play a completely random jingle each time (personal theme songs override this) |
| .getthemesongmode |             /              | Check your current theme song mode in the server.                                                                                                                                                                                                                                                                            |
| .setthemesongmode | [enable/disable]           | Enable (play if a member has one) or disable (ignore) personal theme songs for this server.                                                                                                                                                                                                                                                            |

### User settings

|    Command    |              Usage              |                                                                                                                                                                          Description                                                                                                                                                                         |
|:-------------:|:-------------------------------:|:------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------:|
| .getthemesong |                /                | Check what your current theme song is, if you have one.                                                                                                                                                                                                                                                                                                      |
| .setthemesong | (jingle code/none) | Set your personal theme song. <br>Run command with "none" to remove your theme song. If you know your new theme song (jingle)'s code already, you can add that to the end of the command. If you're not sure yet and want to browse, run the command without additional arguments and  you'll have a chance to pick your favourite new jingle interactively. |

### Misc
| Command | Usage          | Description                                                                                                        |
|---------|----------------|--------------------------------------------------------------------------------------------------------------------|
| .ping   |                | Shows some basic information about Jingler.                                                                        |
| .help   | (command name) | Show a list of available commands. If used with a command name, shows information about the command and its usage. |


# 3. Installation
Currently, I don't run Jingler as a public bot that you could just add to your server.
However, that does not mean that you can't run your own!
Grab a person familiar with setting up Python and/or Discord bots and let's go!

- First make sure you have [Python 3.8+](https://www.python.org/) installed. Then, follow the instructions on [installing Poetry](https://python-poetry.org/docs/#installation), a Python package manager.
- When both Python and Poetry are installed, [clone](https://docs.github.com/en/github/creating-cloning-and-archiving-repositories/cloning-a-repository-from-github/cloning-a-repository) or download the Jingler repository
and store or extract it into a directory of your choosing.
- Install dependencies by running `poetry install`.
- Copy `data/configuration.EXAMPLE.toml` to `data/configuration.toml` and fill out the bot token and server whitelist.
- Start the bot by running `poetry run python jingle_bot.py` or by using `run.sh` (needs `screen` installed) or `run.ps1`.
- And that's it! Enjoy!

If you encounter bugs or have feature ideas (that I may or may not implement), feel free open an [`Issue`](https://github.com/DefaultSimon/jingler/issues).

