echo "Starting Jingler..."

screen -m -d -L -S Jingler poetry run python bot.py

echo "Done! Enter screen with"
echo -e "    screen -r Jingler"

