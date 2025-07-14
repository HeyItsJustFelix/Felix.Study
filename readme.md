# Setting up the bot
Go to the Discord Developers Portal and make a new bot. Make sure to copy the token somewhere safe. Go to the oauth tab and select "Bot" as the Scope, and allow the permissions:

### General Permissions (Used to set up study channels/roles)
- Manage Roles
- Manage Channels
- View Channels

### Text Permissions
- Send Messages
- Create Public Threads
- Create Private Threads
- Send Messages in Threads
- Manage Threads
- Embed Links
- Attach Files
- Mention Everyone (Optional)
- Use External Emojis
- Add Reactions

### Voice Permissions (Used for notification sounds)
- Connect
- Speak
- Move Members

Inside of the Bot tab, turn on the "Server Members Intent" to allow users to use the bot in DMs and to allow us to DM users

# Running the Bot Code
### Windows specific instructions
In order to run the code properly without errors, you must be running Python 3.11 or newer. I highly recommend checking "Add to PATH" during installation so you don't have to reference to the file location. Once you have Python installed, make sure that you're inside of the folder with the code by typing cmd at the top of the file explorer window. Once the command prompt is open, run python.exe -m venv env, then run .\env\Scripts\activate. This will put you into an environment where you can install packages locally. Next, run python.exe -m pip install -r requirements.txt to install the required packages for the bot.

Once you have your venv set up properly, you should be able to run python.exe main.py to run the bot! If your commands do not show up, try restarting Discord.

### Windows troubleshooting
If you receive python.exe not found or something similar, please rerun the installer, click modify, and click next, and make sure that Add python to environment variables is checked, then click Install.

### Linux specific instructions
In order to run the code properly without errors, you must be running Python 3.11 or newer. Once you have Python installed, run python3 -m venv env, then run source ./env/bin/activate. This will put you into an environment where you can install packages locally. Next, run python -m pip install -r requirements.txt to install the required packages for the bot.

Once you have your venv set up properly, you should be able to run python main.py to run the bot! If your commands do not show up, try restarting Discord