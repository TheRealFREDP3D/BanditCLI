# BanditCLI - The OverTheWire Bandit Wargame CLI Tool

## Overview 
This project is a command-line tool for playing the OverTheWire Bandit wargame. It's built with Python and the Textual framework, providing a user-friendly interface within the terminal.

---

## Architecture

Here's a breakdown of its architecture:

`main.py`: This is the core of the application. It uses the Textual framework to create the tabbed layout you see when you run it. It handles user input and coordinates the other components.

`ssh_manager.py`: This module manages the SSH connection to the Bandit game server. It's responsible for connecting, sending your commands, and receiving the output.

`level_info.py`: This component loads and displays information about each Bandit level, like the goals and recommended commands. It gets this data from the bandit_levels.json file.

`ai_mentor.py`: This is the AI assistant. It uses OpenAI's GPT-3.5 to give you hints based on your current level and the commands you've recently used.

`app.tcss`: This file styles the application, defining its colors and layout to make it look good in your terminal.

`bandit_levels.json`: This file is a database of all the Bandit level information, which is displayed in the "Level Info" tab.