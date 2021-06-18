echo "Starting Jingle bot..."
screen -m -d -L -S DiscordJingleBot poetry run python bot.py
echo -e "Done! Enter screen with \n\tscreen -r DiscordJingleBot"
