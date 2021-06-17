echo "Starting Jingle bot..."
screen -m -d -L -S DiscordJingleBot poetry run python jingle_bot.py
echo -e "Done! Enter screen with \n\tscreen -r DiscordJingleBot"
