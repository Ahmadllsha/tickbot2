import os
import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button, Modal, TextInput, Select
import asyncio
import json

# Load or initialize deal data
DEAL_DATA_FILE = "deal_data.json"

def load_deal_data():
    if os.path.exists(DEAL_DATA_FILE):
        try:
            with open(DEAL_DATA_FILE, "r") as file:
                data = json.load(file)
                # Migrate old data to new structure
                for user_id, value in data.items():
                    if isinstance(value, int):  # Old structure
                        data[user_id] = {"deals_completed": value, "total_spent": 0.0}
                return data
        except json.JSONDecodeError:
            return {}  # If the file is empty or contains invalid JSON, return an empty dictionary
    return {}  # If the file doesn't exist, return an empty dictionary

def save_deal_data(data):
    with open(DEAL_DATA_FILE, "w") as file:
        json.dump(data, file, indent=4)

deal_data = load_deal_data()

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
intents.messages = True

bot = commands.Bot(command_prefix="!", intents=intents)

TICKET_CATEGORY_NAME = "Tickets"  # Category for ticket channels
REVIEWS_CHANNEL_ID = 1319287805058220074  # Channel for reviews
embed_message_id = None
ADMIN_IDS = [751941348621287445, 987654321098765432]  # Add admin IDs here
REVIEW_EMBED_IMAGE = "https://media.discordapp.net/attachments/1184666977671852133/1338998043391033344/standard_3.gif?ex=67adc75a&is=67ac75da&hm=e7dc1c6c990d6c54a07e97195501d87ab6da2d914e84ad8082be57ac02a60d2a&="  # Default top-right image
BOTTOM_IMAGE_DEFAULT = "https://media.discordapp.net/attachments/1184666977671852133/1338998042761760798/standard_4.gif?ex=67adc75a&is=67ac75da&hm=489014ea2cde5bf9da327ea890ffe6a9dcafb2b2bc8b777a9a0f0bfaa0659954&="  # Default bottom image

# Customizable embed fields
embed_title = "<:Robux:1305394825914351704> Robux Automation"
embed_description = "This automation bot is specifically designed to provide a range of convenient features:"
embed_fields = [
    {"name": "Instant Delivery", "value": "Enjoy rapid delivery of your Robux, receiving them within moments of your purchase, so you can dive into your gaming experience without delay.", "inline": False},
    {"name": "Secure Transactions", "value": "Our bot guarantees a safe and secure payment process, employing advanced encryption and security measures to protect your financial information.", "inline": False},
    {"name": "Safety First", "value": "At Robux Automation, we prioritize the safety and security of your transactions. Rest assured that your personal details are managed with the utmost care, ensuring a worry-free experience.", "inline": False},
    {"name": "Diverse Payment Methods", "value": "We offer a wide variety of automated payment options, including cryptocurrency, PayPal, and many others, making it easy for you to choose the method that works best for you.", "inline": False}
]
embed_footer = "Thank you for choosing Robux Automation!"

# Stock system (default items empty, only one test item)
stock = {
    "Test Item": {"price": 10.0, "description": "This is a test item for demonstration purposes."}
}

# Cart system
user_carts = {}

# Transaction status
transaction_status = {}

class ItemSelectionView(View):
    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id
        self.item_select = Select(
            placeholder="Select an item to purchase",
            options=[discord.SelectOption(label=item, description=stock[item]["description"]) for item in stock]
        )
        self.add_item(self.item_select)

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Only the ticket owner can interact with this.", ephemeral=True)
            return False

        selected_item = self.item_select.values[0]
        user_carts[self.user_id] = user_carts.get(self.user_id, {})
        user_carts[self.user_id][selected_item] = 0  # Initialize quantity

        await interaction.response.send_message(
            f"How many **{selected_item}** would you like to buy?",
            ephemeral=True
        )

        while True:
            def check(message):
                return message.author.id == self.user_id and message.channel == interaction.channel

            try:
                quantity_message = await bot.wait_for('message', timeout=60.0, check=check)
                quantity = quantity_message.content

                # Check if the user typed "done"
                if quantity.lower() == "done":
                    break

                # Try to convert the input to an integer
                quantity = int(quantity)
                if quantity > 0:
                    user_carts[self.user_id][selected_item] = quantity
                    await interaction.followup.send(
                        f"Added **{quantity} {selected_item}** to your cart.",
                        ephemeral=True
                    )
                    break
                else:
                    await interaction.followup.send("Quantity must be a positive number. Please try again.", ephemeral=True)
            except asyncio.TimeoutError:
                await interaction.followup.send("You took too long to respond. Please start over.", ephemeral=True)
                return
            except ValueError:
                await interaction.followup.send("Invalid input. Please enter a number or type 'done' to finish.", ephemeral=True)

        # Ask if they want to add more items
        add_more_view = View()
        add_more_button = Button(label="Add More", style=discord.ButtonStyle.green, custom_id="add_more")
        done_button = Button(label="Done", style=discord.ButtonStyle.red, custom_id="done")
        remove_button = Button(label="Remove Items", style=discord.ButtonStyle.gray, custom_id="remove_items")
        add_more_view.add_item(add_more_button)
        add_more_view.add_item(done_button)
        add_more_view.add_item(remove_button)

        await interaction.followup.send(
            "Would you like to add more items to your cart or remove items?",
            view=add_more_view,
            ephemeral=True
        )
class RemoveItemsView(View):
    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id
        self.item_select = Select(
            placeholder="Select an item to remove",
            options=[discord.SelectOption(label=item) for item in user_carts[user_id]]
        )
        self.add_item(self.item_select)

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Only the ticket owner can interact with this.", ephemeral=True)
            return False

        selected_item = self.item_select.values[0]
        if selected_item in user_carts[self.user_id]:
            del user_carts[self.user_id][selected_item]
            await interaction.response.send_message(
                f"Removed **{selected_item}** from your cart.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message("Item not found in your cart.", ephemeral=True)

class PaymentMethodDropdown(View):
    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id
        self.crypto_select = Select(
            placeholder="Choose your payment method",
            options=[
                discord.SelectOption(
                    label="Bitcoin",
                    value="BTC",
                    description="Pay with Bitcoin",
                    emoji="<:bitcoin:1305877376969736264>"
                ),
                discord.SelectOption(
                    label="Ethereum",
                    value="ETH",
                    description="Pay with Ethereum",
                    emoji="<:ethw:1305877378207186944>"
                ),
                discord.SelectOption(
                    label="Litecoin",
                    value="LTC",
                    description="Pay with Litecoin",
                    emoji="<:litecoin:1305877374667198504>"
                ),
                discord.SelectOption(
                    label="PayPal",
                    value="PayPal",
                    description="Pay with PayPal",
                    emoji="<:paypal:1305877375854313535>"
                ),
                discord.SelectOption(
                    label="CashApp",
                    value="CashApp",
                    description="Pay with CashApp",
                    emoji="<:CashApp:1305900694426877968>"
                ),
                discord.SelectOption(
                    label="Robux",
                    value="Robux",
                    description="Pay with Robux",
                    emoji="<:Robux:1305394825914351704>"
                ),
                discord.SelectOption(
                    label="Others",
                    value="Others",
                    description="Other payment methods",
                    emoji="❓"
                )
            ]
        )
        self.add_item(self.crypto_select)

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Only the ticket owner can interact with this.", ephemeral=True)
            return False

        payment_method = self.crypto_select.values[0]
        transaction_status[self.user_id] = {"paid": False, "completed": False, "payment_method": payment_method, "buyer_id": self.user_id}

        # Payment details
        payment_details = {
            "BTC": {"title": "Bitcoin Payment", "address": "bc1qvvyyha5qn7fqwfkgl26xrznghl30nzedupwqc8"},
            "ETH": {"title": "Ethereum Payment", "address": "0xf27f0a9e23b41C6a468cb1b64919cB98Ad53e316"},
            "LTC": {"title": "Litecoin Payment", "address": "ltc1q9vpxfhgzjlr0hjm8ffmn5e40znytur5g7lvkvk"},
            "PayPal": {
                "title": "PayPal Payment",
                "description": "Please ping <@1148847073458925668> for PayPal assistance."
            },
            "CashApp": {
                "title": "CashApp Payment",
                "description": (
                    "To proceed with the transaction, please follow these instructions carefully:\n\n"
                    "1. **Send the payment to this CashApp tag:**\n"
                    "**`$Nexus5784`**\n\n"
                    "2. **Important Guidelines:**\n"
                    "- Must send payment from **Balance**, not a **Card**.\n"
                    "- Do not include any **Notes** with your payment.\n"
                    "- Send **$1 first** as a test transaction.\n\n"
                    "⚠️ Sending incorrectly may result in the loss of funds!"
                )
            },
            "Robux": {
                "title": "Robux Payment",
                "description": (
                    "To proceed with the transaction, please follow these instructions carefully:\n\n"
                    "1. **Send the Robux to this user:**\n"
                    "**`RobuxReceiver123`**\n\n"
                    "2. **Important Guidelines:**\n"
                    "- Include the transaction ID in the notes.\n"
                    "- Ensure the Robux amount matches your purchase.\n\n"
                    "⚠️ Failure to follow these instructions may result in delays!"
                )
            },
            "Others": {
                "title": "Other Payment Methods",
                "description": "Please wait for the seller or an admin to assist you."
            }
        }

        selected_payment = payment_details[payment_method]

        embed_payment = discord.Embed(
            title=selected_payment["title"],
            color=discord.Color.green()
        )

        if payment_method == "Others":
            embed_payment.description = selected_payment["description"]
        elif payment_method == "CashApp":
            embed_payment.description = selected_payment["description"]
        elif payment_method == "PayPal":
            embed_payment.description = selected_payment["description"]
        elif payment_method == "Robux":
            embed_payment.description = selected_payment["description"]
        else:
            embed_payment.description = (
                f"To proceed with the transaction, please send the required payment to the following address:\n"
                f"**```{selected_payment['address']}```**\n\n"
            )

        embed_payment.set_footer(text="Copy the address and complete your payment.")
        embed_payment.set_thumbnail(url=REVIEW_EMBED_IMAGE)  # Image in top-right

        # Mark as Paid button
        mark_as_paid_button = Button(label="Mark as Paid", style=discord.ButtonStyle.green, custom_id="mark_as_paid")
        cancel_button = Button(label="Cancel", style=discord.ButtonStyle.red, custom_id="cancel_ticket")

        view = View()
        view.add_item(mark_as_paid_button)
        view.add_item(cancel_button)

        await interaction.response.send_message(
            embed=embed_payment,
            view=view,
            ephemeral=True
        )

class ReviewModal(Modal, title="Leave a Review"):
    review = TextInput(label="Your Review", placeholder="Share your experience...", style=discord.TextStyle.long, required=True)
    stars = TextInput(label="Star Rating (1-5)", placeholder="Enter a number between 1 and 5", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            stars = int(self.stars.value)
            if stars < 1 or stars > 5:
                await interaction.response.send_message("Please enter a star rating between 1 and 5.", ephemeral=True)
                return
        except ValueError:
            await interaction.response.send_message("Invalid star rating. Please enter a number between 1 and 5.", ephemeral=True)
            return

        reviews_channel = bot.get_channel(REVIEWS_CHANNEL_ID)
        if reviews_channel:
            user = interaction.user
            cart = user_carts.get(user.id, {})
            total_price = sum(stock[item]["price"] * quantity for item, quantity in cart.items())
            payment_method = transaction_status[user.id]["payment_method"]

            embed = discord.Embed(
                title="New Review",
                description=self.review.value,
                color=discord.Color.green()
            )
            embed.set_author(name=user.display_name, icon_url=user.avatar.url)
            embed.add_field(name="Items Purchased", value="\n".join([f"{item} x{quantity}" for item, quantity in cart.items()]), inline=False)
            embed.add_field(name="Total Price", value=f"${total_price:.2f}", inline=False)
            embed.add_field(name="Payment Method", value=payment_method, inline=False)
            embed.add_field(name="Star Rating", value="⭐" * stars, inline=False)
            embed.set_thumbnail(url=REVIEW_EMBED_IMAGE)  # Image in top-right

            await reviews_channel.send(embed=embed)
            await interaction.response.send_message("Thank you for your review!", ephemeral=True)
        else:
            await interaction.response.send_message("Reviews channel not found. Please contact an admin.", ephemeral=True)

@bot.event
async def on_ready():
    print(f"Bot is online and ready. Logged in as {bot.user}")

    # Sync all commands with Discord
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands.")
    except Exception as e:
        print(f"Failed to sync commands: {e}")


@bot.event
async def on_message(message):
    # Ignore messages from the bot itself
    if message.author == bot.user:
        return

    # Handle prefix-based commands
    if message.content.startswith(BOT_PREFIX):
        # Extract the command and arguments
        command = message.content[len(BOT_PREFIX):].split()[0]
        args = message.content[len(BOT_PREFIX) + len(command):].strip()

        # Example: Handle a prefix-based help command
        if command == "help":
            await message.channel.send("Use `/help` for a list of commands.")

    # Ensure other events (like on_interaction) are still processed
    await bot.process_commands(message)

@bot.tree.command(name="help", description="Show all available commands.")
async def help(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Available Commands",
        description="Here are all the commands you can use:",
        color=discord.Color.blue()
    )

    # General Commands
    embed.add_field(
        name="General Commands",
        value=(
            "`/help` - Show this message.\n"
            "`/purchase` - Start a purchase ticket.\n"
            "`/leave_review` - Leave a review for your purchase."
        ),
        inline=False
    )

    # Admin Commands
    if interaction.user.id in ADMIN_IDS:
        embed.add_field(
            name="Admin Commands",
            value=(
                "`/setup_embed` - Set up the purchase embed.\n"
                "`/create_embed` - Create a custom embed.\n"
                "`/add_item` - Add an item to the stock.\n"
                "`/remove_item` - Remove an item from the stock.\n"
                "`/set_review_image` - Set the review embed image.\n"
                "`/delete_all` - Delete all active tickets.\n"
                "`/add` - Add a user to a ticket.\n"
                "`/delete` - Delete the current ticket.\n"
                "`/change_prefix` - Change the bot's command prefix."
            ),
            inline=False
        )

    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="setup_embed", description="Set up the embed in the current channel. (Admin Only)")
async def setup_embed(interaction: discord.Interaction):
    if interaction.user.id not in ADMIN_IDS:
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    global embed_message_id

    embed = discord.Embed(
        title=embed_title,
        description=embed_description,
        color=0x8000FF  
    )

    for field in embed_fields:
        embed.add_field(name=field["name"], value=field["value"], inline=field["inline"])

    embed.set_footer(text=embed_footer)
    embed.set_thumbnail(url=REVIEW_EMBED_IMAGE)  # Image in top-right

    purchase_button = Button(label="Purchase", style=discord.ButtonStyle.green, emoji="💸", custom_id="purchase")

    view = View()
    view.add_item(purchase_button)

    sent_message = await interaction.channel.send(embed=embed, view=view)

    embed_message_id = sent_message.id
    await interaction.response.send_message("Embed set up successfully!", ephemeral=True)

@bot.tree.command(name="create_embed", description="Create a custom embed in the current channel. (Admin Only)")
async def create_embed(
    interaction: discord.Interaction,
    title: str,
    description: str,
    footer: str,
    top_right_image: str = None,
    bottom_image: str = None
):
    if interaction.user.id not in ADMIN_IDS:
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    # Use default images if none are provided
    if not top_right_image:
        top_right_image = REVIEW_EMBED_IMAGE
    if not bottom_image:
        bottom_image = BOTTOM_IMAGE_DEFAULT

    embed = discord.Embed(
        title=title,
        description=description,
        color=0x8000FF  
    )

    embed.set_footer(text=footer)
    embed.set_thumbnail(url=top_right_image)  # Top-right image
    embed.set_image(url=bottom_image)  # Bottom image

    await interaction.channel.send(embed=embed)
    await interaction.response.send_message("Custom embed created successfully!", ephemeral=True)

@bot.tree.command(name="add_item", description="Add an item to the stock. (Admin Only)")
async def add_item(interaction: discord.Interaction, name: str, price: float, description: str):
    if interaction.user.id not in ADMIN_IDS:
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    global stock

    stock[name] = {"price": price, "description": description}
    await interaction.response.send_message(f"Added **{name}** to the stock.", ephemeral=True)

@bot.tree.command(name="remove_item", description="Remove an item from the stock. (Admin Only)")
async def remove_item(interaction: discord.Interaction, name: str):
    if interaction.user.id not in ADMIN_IDS:
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    global stock

    if name in stock:
        del stock[name]
        await interaction.response.send_message(f"Removed **{name}** from the stock.", ephemeral=True)
    else:
        await interaction.response.send_message(f"Item **{name}** not found in stock.", ephemeral=True)

@bot.tree.command(name="set_review_image", description="Set the image for review embeds. (Admin Only)")
async def set_review_image(interaction: discord.Interaction, image_url: str):
    if interaction.user.id not in ADMIN_IDS:
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    global REVIEW_EMBED_IMAGE
    REVIEW_EMBED_IMAGE = image_url
    await interaction.response.send_message(f"Review embed image updated to: {image_url}", ephemeral=True)

@bot.tree.command(name="delete_all", description="Delete all active tickets in the ticket category. (Admin Only)")
async def delete_all(interaction: discord.Interaction):
    if interaction.user.id not in ADMIN_IDS:
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    guild = interaction.guild
    category = discord.utils.get(guild.categories, name=TICKET_CATEGORY_NAME)

    if not category:
        await interaction.response.send_message("Ticket category not found.", ephemeral=True)
        return

    deleted_count = 0
    for channel in category.channels:
        if isinstance(channel, discord.TextChannel) and channel.name.startswith("ticket-"):
            await channel.delete()
            deleted_count += 1

    await interaction.response.send_message(f"Deleted {deleted_count} tickets.", ephemeral=True)

@bot.tree.command(name="add", description="Add a user to the current ticket. (Admin Only)")
async def add(interaction: discord.Interaction, user: discord.Member):
    if interaction.user.id not in ADMIN_IDS:
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    if not isinstance(interaction.channel, discord.TextChannel) or not interaction.channel.name.startswith("ticket-"):
        await interaction.response.send_message("This command can only be used in a ticket channel.", ephemeral=True)
        return

    await interaction.channel.set_permissions(user, read_messages=True, send_messages=True)
    await interaction.response.send_message(f"Added {user.mention} to the ticket.", ephemeral=True)


@bot.tree.command(name="delete", description="Delete the current ticket. (Admin Only)")
async def delete(interaction: discord.Interaction):
    if interaction.user.id not in ADMIN_IDS:
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    if not isinstance(interaction.channel, discord.TextChannel) or not interaction.channel.name.startswith("ticket-"):
        await interaction.response.send_message("This command can only be used in a ticket channel.", ephemeral=True)
        return

    await interaction.response.send_message("Deleting this ticket...", ephemeral=True)
    await interaction.channel.delete()




# Add this at the top of your code (with other global variables)
BOT_PREFIX = "!"

@bot.tree.command(name="change_prefix", description="Change the bot's command prefix. (Admin Only)")
async def change_prefix(interaction: discord.Interaction, new_prefix: str):
    if interaction.user.id not in ADMIN_IDS:
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    global BOT_PREFIX
    BOT_PREFIX = new_prefix

    # Update the bot's command prefix
    bot.command_prefix = BOT_PREFIX

    await interaction.response.send_message(f"Command prefix changed to `{BOT_PREFIX}`.", ephemeral=True)
















@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type == discord.InteractionType.component:
        if 'custom_id' in interaction.data:
            custom_id = interaction.data['custom_id']
            user_id = interaction.user.id

            if custom_id == "purchase":
                user = interaction.user
                guild = interaction.guild

                # Find or create the ticket category
                category = discord.utils.get(guild.categories, name=TICKET_CATEGORY_NAME)
                if not category:
                    category = await guild.create_category(TICKET_CATEGORY_NAME)

                # Create the ticket channel
                ticket_channel = await guild.create_text_channel(
                    name=f"ticket-{user.name}",
                    category=category,
                    reason="Purchase ticket"
                )

                # Set permissions for the ticket channel
                await ticket_channel.set_permissions(user, read_messages=True, send_messages=True)
                await ticket_channel.set_permissions(guild.default_role, read_messages=False)

                await interaction.response.send_message(
                    f"Ticket created: <#{ticket_channel.id}>",
                    ephemeral=True
                )

                # Welcome message with cancel option
                cancel_button = Button(label="Cancel", style=discord.ButtonStyle.red, custom_id="cancel_ticket")
                view = View()
                view.add_item(cancel_button)

                await ticket_channel.send(
                    f"{user.mention}, welcome to your ticket! Let's proceed with your purchase.",
                    view=view
                )

                # Initialize transaction status for the user
                transaction_status[user.id] = {"paid": False, "completed": False, "buyer_id": user.id}

                # Use ItemSelectionView to allow the buyer to select items
                view = ItemSelectionView(user.id)
                await ticket_channel.send("Please select an item to purchase:", view=view)

            elif custom_id == "mark_as_paid":
                transaction_status[user_id]["paid"] = True

                # Show a public embed with purchase details
                cart = user_carts.get(user_id, {})
                total_price = sum(stock[item]["price"] * quantity for item, quantity in cart.items())
                payment_method = transaction_status[user_id]["payment_method"]

                embed = discord.Embed(
                    title="Payment Marked as Paid",
                    description=f"{interaction.user.mention} has marked their payment as paid.",
                    color=discord.Color.green()
                )
                embed.add_field(name="Items Purchased", value="\n".join([f"{item} x{quantity}" for item, quantity in cart.items()]), inline=False)
                embed.add_field(name="Total Price", value=f"${total_price:.2f}", inline=False)
                embed.add_field(name="Payment Method", value=payment_method, inline=False)
                embed.set_thumbnail(url=REVIEW_EMBED_IMAGE)  # Image in top-right

                await interaction.channel.send(embed=embed)

                # Deal Completed button for admins
                # Include the buyer's ID in the custom_id
                deal_completed_button = Button(
                    label="Deal Completed",
                    style=discord.ButtonStyle.green,
                    custom_id=f"deal_completed_{user_id}"  # Store the buyer's ID in the custom_id
                )
                view = View()
                view.add_item(deal_completed_button)

                await interaction.response.send_message(
                    "Payment marked as paid. Waiting for admin to complete the deal.",
                    view=view
                )

            elif custom_id.startswith("deal_completed_"):
                # Extract the buyer's ID from the custom_id
                buyer_id = int(custom_id.split("_")[2])

                # Check if the user is an admin
                if interaction.user.id not in ADMIN_IDS:
                    await interaction.response.send_message("You do not have permission to complete the deal.", ephemeral=True)
                    return

                # Show Leave a Review button (only for the ticket owner)
                leave_review_button = Button(label="Leave a Review", style=discord.ButtonStyle.green, custom_id="leave_review")
                view = View()
                view.add_item(leave_review_button)

                embed = discord.Embed(
                    title="Deal Completed",
                    description=f"{interaction.user.mention}, give a review. If you don't, you will be blacklisted.",
                    color=discord.Color.green()
                )
                embed.set_thumbnail(url=REVIEW_EMBED_IMAGE)  # Image in top-right

                await interaction.response.send_message(
                    embed=embed,
                    view=view
                )

            elif custom_id == "leave_review":
                if interaction.user.id != transaction_status[user_id]["buyer_id"]:
                    await interaction.response.send_message("Only the ticket owner can leave a review.", ephemeral=True)
                    return

                # Ask for review
                review_modal = ReviewModal()
                await interaction.response.send_modal(review_modal)

            elif custom_id == "cancel_ticket":
                if isinstance(interaction.channel, discord.TextChannel) and interaction.channel.name.startswith("ticket-"):
                    await interaction.response.send_message("Closing and deleting this ticket...", ephemeral=True)
                    await interaction.channel.delete()
                else:
                    await interaction.response.send_message("This command can only be used in a ticket channel.", ephemeral=True)

            elif custom_id == "add_more":
                view = ItemSelectionView(user_id)
                await interaction.response.send_message("Please select another item to purchase:", view=view, ephemeral=True)

            elif custom_id == "remove_items":
                if user_id not in user_carts or not user_carts[user_id]:
                    await interaction.response.send_message("Your cart is empty.", ephemeral=True)
                    return

                view = RemoveItemsView(user_id)
                await interaction.response.send_message("Select an item to remove from your cart:", view=view, ephemeral=True)

            elif custom_id == "done":
                user = interaction.user
                cart = user_carts.get(user_id, {})

                if not cart:
                    await interaction.response.send_message("Your cart is empty.", ephemeral=True)
                    return

                total_price = sum(stock[item]["price"] * quantity for item, quantity in cart.items())
                embed = discord.Embed(
                    title="Your Cart",
                    description="Here are the items in your cart:",
                    color=discord.Color.blue()
                )

                for item, quantity in cart.items():
                    embed.add_field(
                        name=item,
                        value=f"Quantity: {quantity}\nPrice: ${stock[item]['price'] * quantity:.2f}",
                        inline=False
                    )

                embed.add_field(
                    name="Total Price",
                    value=f"${total_price:.2f}",
                    inline=False
                )

                embed.set_footer(text="Proceed to payment.")
                embed.set_thumbnail(url=REVIEW_EMBED_IMAGE)  # Image in top-right

                await interaction.response.send_message(embed=embed, view=PaymentMethodDropdown(user_id), ephemeral=True)
bot.run("MTMzODY1MTgxNjMxNjg5OTQzOQ.G0LUlR.qqQfCTp1aueC2zowNAbcum-tCoYsttcM5M85uc")