import discord
import warnings
from etl.load_config import etl
from utils.board import board
from utils.game_functions import game_utils
warnings.filterwarnings("ignore")


# Set up Discord client with specific intents to handle messages and reactions
intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
client = discord.Client(intents=intents)


# Event handler for when the bot is ready and connected to the Discord server
@client.event
async def on_ready():
    # Generate and send the initial game board to the specified channel
    board.generate_board(tiles, board_data, teams)
    await client.get_channel(board_channel).send(file=discord.File('game_board.png'))
    print(f'We have logged in as {client.user}')


# Event handler for incoming messages
@client.event
async def on_message(message):
    # Ignore messages sent by the bot itself
    if message.author == client.user:
        return
    
    # Handle messages in the image submission channel
    if message.channel.id == image_channel_id:
        if message.attachments:
            # Find the team name of the user who submitted the image
            team_name = game_utils.find_team_name(message.author, teams)
            user_id = 165559954516738049

            # Notify in the designated notification channel about the image submission
            await client.get_channel(notification_channel_id).send(f"**{team_name}** just uploaded a drop - Waiting for approval from <@{user_id}>")

    # Handle messages in the notification channel with the "!reroll" command
    if message.channel.id == notification_channel_id and message.content == "!reroll":

        # Find the team name of the user who sent the command
        team_name = game_utils.find_team_name(message.author, teams)

        # Check if the team has remaining rerolls
        if teams[team_name]["rerolls"] == 0:
            await client.get_channel(notification_channel_id).send(f'Requesting team **{team_name}** does not have any rerolls left - too bad!')
        else:
            # Perform a reroll for the team and update the game state
            old_tile_name = tiles[f"tile{teams[team_name]['tile']}"]["item-name"]
            last_roll = teams[team_name]["last_roll"]
            teams[team_name]["tile"] -= last_roll
            dice_roll = game_utils.roll_dice()
            game_utils.update_team_tiles(teams[team_name], dice_roll)
            game_utils.update_last_roll(teams[team_name], dice_roll)
            new_tile_name = tiles[f"tile{teams[team_name]['tile']}"]["item-name"]
            new_tile_desc = tiles[f"tile{teams[team_name]['tile']}"]["tile-desc"]

            # Only use the reroll token if the new roll is different from the last roll
            if last_roll != dice_roll:
                teams[team_name]["rerolls"] -= 1

            # Notify the team about the reroll result and update the game board
            await client.get_channel(notification_channel_id).send(f'Rerolling for team **{team_name}** from **{old_tile_name}** 🎲 ... \
                                                                \nNew roll is: **{dice_roll}** new tile is **{new_tile_name}** you have **{teams[team_name]["rerolls"]}** rerolls left! \
                                                                \n**Description:** {new_tile_desc}.')
            board.generate_board(tiles, board_data, teams)
            await client.get_channel(board_channel).send(file=discord.File('game_board.png'))


# Event handler for adding reactions to messages
@client.event
async def on_reaction_add(reaction, user):
    # Ignore reactions from other bots
    if user.bot:
        return
    
    # Handle reactions in the image submission channel
    if reaction.message.channel.id == image_channel_id and str(reaction.emoji) == '✅':
         
        # Find the team name of the user who submitted the image
        team_name = game_utils.find_team_name(reaction.message.author, teams)
        dice_roll = game_utils.roll_dice()
        old_tile_name = tiles[f"tile{teams[team_name]['tile']}"]["item-name"]

        # Update the team's position based on the dice roll
        game_utils.update_team_tiles(teams[team_name], dice_roll)
        game_utils.update_last_roll(teams[team_name], dice_roll)
        new_tile_name = tiles[f"tile{teams[team_name]['tile']}"]["item-name"]
        new_tile_desc = tiles[f"tile{teams[team_name]['tile']}"]["tile-desc"]
        
        # Notify the team about the roll result and update the game board
        await client.get_channel(notification_channel_id).send(f'Drop for **{old_tile_name}** was approved 🎲 rolling for **{team_name}** ... \
                                                               \nRoll is: **{dice_roll}** new tile is **{new_tile_name}** good luck! \
                                                               \n**Description:** {new_tile_desc}.')
        board.generate_board(tiles, board_data, teams)
        await client.get_channel(board_channel).send(file=discord.File('game_board.png'))

    # Handle reactions in the image submission channel when the drop is declined
    elif reaction.message.channel.id == image_channel_id and str(reaction.emoji) == '❌':

        # Find the team name of the user who submitted the image and notify the team about the declined drop
        team_name = game_utils.find_team_name(reaction.message.author, teams)
        await client.get_channel(notification_channel_id).send(f'Drop was declined for **{team_name}** check your image and try again!\n')


if __name__ == "__main__":
    # Load configuration data, secrets, and initialize channels and tokens
    board_data, tiles, teams = etl.load_config_file()
    secrets = etl.load_secrets()

    image_channel_id = secrets["image_channel_id"]  # Channel ID for image submissions
    notification_channel_id = secrets["notification_channel_id"]  # Channel ID for notifications
    board_channel = secrets["board_channel"]  # Channel ID for the game board display
    
    # Run the Discord bot with the specified token
    client.run(secrets["discord-bot-token"])