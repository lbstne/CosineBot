import discord
import openai
import urllib
import re
import os
from bs4 import BeautifulSoup

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

openai.api_key = os.environ['OPENAI_API_KEY']

prompt = open('prompt.txt', mode='r').read()
admins = open('admins.txt', mode='r').read().split()

no_reacting = open('no_react.txt', mode='r').read().split()

user_message_histories = {}

system_prompts = [{"role": "system", "content": prompt}]


@client.event
async def on_reaction_add(reaction, user):
    if reaction.message.author.id == user.id:
        await reaction.remove(user)
        await reaction.message.reply("I see that self react :facepalm:")
    elif str(user.id) in no_reacting:
        await reaction.remove(user)
        await reaction.message.reply("Stop fucking reacting, " + user.name)


def url_to_text(matchobject):
    url_string = matchobject.group(0)
    url = url_string[2:-2]

    html_page = urllib.request.urlopen(url).read().decode("utf8")

    return 'Contents from' + url + ': "' + BeautifulSoup(html_page).get_text() + '"'


@client.event
async def on_ready():
    print(f'logged in as: {client.user}')

@client.event
async def on_message(message):
    # prevent it from replying to itself
    if client.user in message.mentions and message.author.id is not client.user:

        # replace [[url]] with actual content from web page
        await message.channel.typing()
        formatted_message = re.sub('\\[\\[.*\\]\\]', url_to_text, message.content)

        # change system prompt at will
        if str(message.author.id) in admins and message.content.contains("{{ADMIN OVERRIDE}}"):
            print("ADMIN OVERRIDE")
            system_prompts.append({"role": "system", "content": formatted_message})
            message_to_send = system_prompts
        else:
            if message.author.id not in user_message_histories:
                # provide some context about the user
                user_message_histories[message.author.id] = [{"role": "system", "content": "The user's name is " + message.author.name}]

            user_message_histories[message.author.id].append({"role": "user", "content": formatted_message})
            message_to_send = system_prompts + user_message_histories[message.author.id]

        msg = ""

        try:
            completion = openai.ChatCompletion.create(model='gpt-4', messages=message_to_send)
            msg = completion.choices[0].message.content

        # error handling on API side
        except openai.error.APIError as e:
            msg = f"I'm sorry {message.author.id}, I can't do that for you."
            print(f"API had an error: {e}")

        except openai.error.Timeout as e:
            msg = f"I'm sorry {message.author.id}. I timed out. Maybe try again?"
            print(f"Request timeout: {e}")

        except openai.error.RateLimitError as e:
            msg = "Wow, you're a fast bugger aren't you? Chill on the requests for a second."
            print("Rate limit hit.")

        except openai.error.APIConnectionError as e:
            msg = f"I'm sorry {message.author.id}, I can't do that for you."
            print(f"API had an error: {e}")

        except openai.error.InvalidRequestError as e:
            msg = "Whoever wrote this bot did a shitty job, so tell them to fix it."
            print(f"Invalid request: {e}")

        except openai.error.AuthenticationError as e:
            msg = "Luca's token failed. LMAO RIP BOZO"
            print(f"Failed auth: {e}")

        except openai.error.ServiceUnavailableError as e:
            msg = "Question for you. What's better than octopus recipe? Answer for you: 8 recipes for octopus. My grandmother give me a family recipe before she died in a horrible way."
            print(f"Check OpenAI's status page: {e}")

        await message.reply(msg)

client.run(os.environ['DISCORD_API_KEY'])
