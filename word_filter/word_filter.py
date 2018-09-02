"""Word Filter cog.
To filter words in a more smart/useful wya than simply detecting and
deleting a message.
"""

import os
import re
import random
import asyncio
from threading import Lock
import discord
from discord.ext import commands
from __main__ import send_cmd_help # pylint: disable=no-name-in-module
from cogs.utils.dataIO import dataIO
from cogs.utils import checks
from cogs.utils.paginator import Pages

COLOUR = discord.Colour

def checkFileSystem():
    """Check if the folders/files are created."""

    folders = ["data/word_filter"]
    for folder in folders:
        if not os.path.exists(folder):
            print("Word Filter: Creating folder: {} ...".format(folder))
            os.makedirs(folder)

    files = ["data/word_filter/filter.json",
             "data/word_filter/settings.json",
             "data/word_filter/whitelist.json"]
    for file in files:
        if not os.path.exists(file):
            #build a default filter.json
            empty = {}
            dataIO.save_json(file, empty)
            print("Word Filter: Creating file: {} ...".format(file))

class WordFilter(): # pylint: disable=too-many-instance-attributes
    """Word Filter cog, for all your word filtering needs."""

    def __init__(self, bot):
        self.bot = bot
        self.lock = Lock()
        self.lock_settings = Lock()
        self.filters = dataIO.load_json("data/word_filter/filter.json")
        self.whitelist = dataIO.load_json("data/word_filter/whitelist.json")
        self.settings = dataIO.load_json("data/word_filter/settings.json")
        self.colours = [COLOUR.purple(),
                        COLOUR.red(),
                        COLOUR.blue(),
                        COLOUR.orange(),
                        COLOUR.green()]

        #JSON keys for settings:
        self.keyToggleMod = "toggleMod"

    def _updateFilters(self, newObj):
        self.lock.acquire()
        try:
            dataIO.save_json("data/word_filter/filter.json", newObj)
            self.filters = dataIO.load_json("data/word_filter/filter.json")
        finally:
            self.lock.release()

    def _updateWhitelist(self, newObj):
        self.lock.acquire()
        try:
            dataIO.save_json("data/word_filter/whitelist.json", newObj)
            self.whitelist = dataIO.load_json("data/word_filter/whitelist.json")
        finally:
            self.lock.release()

    def _updateSettings(self, newObj):
        self.lock_settings.acquire()
        try:
            dataIO.save_json("data/word_filter/settings.json", newObj)
            self.settings = dataIO.load_json("data/word_filter/settings.json")
        finally:
            self.lock_settings.release()

    @commands.group(name="word_filter", pass_context=True, no_pm=True, aliases=["wf"])
    @checks.mod_or_permissions(manage_messages=True)
    async def wordFilter(self, ctx):
        """Smart word filtering"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @wordFilter.command(name="add", pass_context=True, no_pm=True)
    @checks.mod_or_permissions(manage_messages=True)
    async def addFilter(self, ctx, word: str):
        """Add word to filter"""
        guildId = ctx.message.server.id
        user = ctx.message.author
        guildName = ctx.message.server.name

        if guildId not in list(self.filters):
            myDict = {}
            myDict[guildId] = []
            self.filters.update(myDict)
            self._updateFilters(self.filters)

        if word not in self.filters[guildId]:
            self.filters[guildId].append(word)
            self._updateFilters(self.filters)
            await self.bot.send_message(user,
                                        "`Word Filter:` `{0}` was added to the filter "
                                        "in the guild **{1}**".format(word, guildName))
        else:
            await self.bot.send_message(user,
                                        "`Word Filter:` The word `{0}` is already in "
                                        "the filter for guild **{1}**".format(word, guildName))

    @wordFilter.command(name="remove", pass_context=True, no_pm=True)
    @checks.mod_or_permissions(manage_messages=True)
    async def removeFilter(self, ctx, word: str):
        """Remove word from filter"""
        guildId = ctx.message.server.id
        user = ctx.message.author
        guildName = ctx.message.server.name

        if guildId not in list(self.filters):
            await self.bot.send_message(user,
                                        "`Word Filter:` The guild **{}** is not "
                                        "registered, please add a word first".format(guildName))
            return

        if not self.filters[guildId] or word not in self.filters[guildId]:
            await self.bot.send_message(user,
                                        "`Word Filter:` The word `{0}` is not in the "
                                        "filter for guild **{1}**".format(word, guildName))
        else:
            self.filters[guildId].remove(word)
            self._updateFilters(self.filters)
            await self.bot.send_message(user,
                                        "`Word Filter:` `{0}` removed from the filter "
                                        "in the guild **{1}**".format(word, guildName))

    @wordFilter.command(name="list", pass_context=True, no_pm=True)
    @checks.mod_or_permissions(manage_messages=True)
    async def listFilter(self, ctx):
        """List filtered words in raw format.
        NOTE: do this in a channel outside of the viewing public
        """
        guildId = ctx.message.server.id
        guildName = ctx.message.server.name
        user = ctx.message.author

        if guildId not in list(self.filters):
            await self.bot.send_message(user,
                                        "`Word Filter:` The guild **{}** is not "
                                        "registered, please add a word first".format(guildName))
            return

        if self.filters[guildId]:
            display = []
            for regex in self.filters[guildId]:
                display.append("`{}`".format(regex))
            # msg = ""
            # for word in self.filters[guildId]:
                # msg += word
                # msg += "\n"
            # title = "Filtered words for: **{}**".format(guildName)
            # embed = discord.Embed(title=title,description=msg,colour=discord.Colour.red())
            # await self.bot.send_message(user,embed=embed)

            page = Pages(self.bot, message=ctx.message, entries=display)
            page.embed.title = "Filtered words for: **{}**".format(guildName)
            page.embed.colour = discord.Colour.red()
            await page.paginate()
        else:
            await self.bot.send_message(user,
                                        "Sorry you have no filtered words in "
                                        "**{}**".format(guildName))

    @wordFilter.command(name="togglemod", pass_context=True, no_pm=True)
    @checks.mod_or_permissions(manage_messages=True)
    async def toggleMod(self, ctx):
        """Toggle global override of filters for server admins/mods."""
        self._updateSettings(self.settings)
        try:
            if self.settings[ctx.message.author.server.id][self.keyToggleMod] is True:
                self.settings[ctx.message.author.server.id][self.keyToggleMod] = False
                isSet = False
            else:
                self.settings[ctx.message.author.server.id][self.keyToggleMod] = True
                isSet = True
        except KeyError:
            if ctx.message.author.server.id not in self.settings:
                self.settings[ctx.message.author.server.id] = {}
            self.settings[ctx.message.author.server.id][self.keyToggleMod] = True
            isSet = True
        self._updateSettings(self.settings)
        if isSet:
            await self.bot.say(":white_check_mark: Word Filter: Moderators (and "
                               "higher) **will not be** filtered.")
        else:
            await self.bot.say(":negative_squared_cross_mark: Word Filter: Moderators "
                               "(and higher) **will be** filtered.")

        self._updateSettings(self.settings)

    ############################################
    # COMMANDS - CHANNEL WHITELISTING SETTINGS #
    ############################################
    @wordFilter.group(name="whitelist", pass_context=True, no_pm=True,
                      aliases=["wl"])
    @checks.mod_or_permissions(manage_messages=True)
    async def _whitelist(self, ctx):
        """Channel whitelisting settings."""
        if str(ctx.invoked_subcommand).lower() == "word_filter whitelist":
            await send_cmd_help(ctx)

    @_whitelist.command(name="add", pass_context=True, no_pm=True)
    @checks.mod_or_permissions(manage_messages=True)
    async def _whitelistAdd(self, ctx, channelName: str):
        """Add channel to whitelist.
        All messages in the channel will not be filtered.
        """
        guildId = ctx.message.server.id

        if guildId not in list(self.whitelist):
            myDict = {}
            myDict[guildId] = []
            self.whitelist.update(myDict)
            self._updateWhitelist(self.whitelist)

        if channelName not in self.whitelist[guildId]:
            self.whitelist[guildId].append(channelName)
            self._updateWhitelist(self.whitelist)
            await self.bot.say(":white_check_mark: Word Filter: Channel with name "
                               "`{0}` will not be filtered.".format(channelName))
        else:
            await self.bot.say(":negative_squared_cross_mark: Word Filter: Channel "
                               "`{0}` is already whitelisted.".format(channelName))

    @_whitelist.command(name="remove", pass_context=True, no_pm=True,
                        aliases=["delete"])
    @checks.mod_or_permissions(manage_messages=True)
    async def _whitelistRemove(self, ctx, channelName: str):
        """Remove channel from whitelist
        All messages in the removed channel will be subjected to the filter.
        """
        guildId = ctx.message.server.id
        guildName = ctx.message.server.name

        if guildId not in list(self.whitelist):
            await self.bot.say(":negative_squared_cross_mark: Word Filter: The "
                               "guild **{}** is not registered, please add a "
                               "channel to the whitelist first.".format(guildName))
            return

        if not self.whitelist[guildId] or channelName not in self.whitelist[guildId]:
            await self.bot.say(":negative_squared_cross_mark: Word Filter: Channel "
                               "`{0}` was already not whitelisted.".format(channelName))
        else:
            self.whitelist[guildId].remove(channelName)
            self._updateWhitelist(self.whitelist)
            await self.bot.say(":white_check_mark: Word Filter: `{0}` removed from "
                               "the channel whitelist.".format(channelName))

    @_whitelist.command(name="list", pass_context=True, no_pm=True)
    @checks.mod_or_permissions(manage_messages=True)
    async def _whitelistList(self, ctx):
        """List whitelisted channels.
        NOTE: do this in a channel outside of the viewing public
        """
        guildId = ctx.message.server.id
        guildName = ctx.message.server.name

        if guildId not in list(self.whitelist):
            await self.bot.say(":negative_squared_cross_mark: Word Filter: The "
                               "guild **{}** is not registered, please add a "
                               "channel first".format(guildName))
            return

        if self.whitelist[guildId]:
            display = []
            for channel in self.whitelist[guildId]:
                display.append("`{}`".format(channel))
            # msg = ""
            # for word in self.whitelist[guildId]:
                # msg += word
                # msg += "\n"
            # title = "Filtered words for: **{}**".format(guildName)
            # embed = discord.Embed(title=title,description=msg,colour=discord.Colour.red())
            # await self.bot.send_message(user,embed=embed)

            page = Pages(self.bot, message=ctx.message, entries=display)
            page.embed.title = "Whitelisted channels for: **{}**".format(guildName)
            page.embed.colour = discord.Colour.red()
            await page.paginate()
        else:
            await self.bot.say("Sorry, there are no whitelisted channels in "
                               "**{}**".format(guildName))

    async def checkWords(self, msg, newMsg=None): \
        # pylint: disable=too-many-branches,too-many-locals
        """This method, given a message, will check to see if the message contains
        any filterable words, and if it does, deletes the original message and
        sends another message with the filterable words censored.
        """
        modRole = self.bot.settings.get_server_mod(msg.server).lower()
        adminRole = self.bot.settings.get_server_admin(msg.server).lower()

        # Filter only configured servers, not private DMs.
        if isinstance(msg.channel, discord.PrivateChannel) or msg.server.id not \
            in list(self.filters):
            return

        guildId = msg.server.id

        # Do not filter whitelisted channels
        try:
            whitelist = self.whitelist[guildId]
            for channels in whitelist:
                if channels.lower() == msg.channel.name.lower():
                    return
        except: # pylint: disable=bare-except
            # Most likely no whitelisted channels.
            pass

        #Check if mod or admin, and do not filter if togglemod is enabled.
        try:
            if self.settings[msg.author.server.id][self.keyToggleMod] is True:
                for role in msg.author.roles:
                    if role.name.lower() == modRole or role.name.lower() == adminRole:
                        return
        except Exception as error: # pylint: disable=broad-except
            print(error)

        filteredWords = self.filters[guildId]
        if newMsg:
            checkMsg = newMsg.content
        else:
            checkMsg = msg.content
        originalMsg = checkMsg
        filteredMsg = originalMsg
        oneWord = _isOneWord(checkMsg)

        for word in filteredWords:
            try:
                filteredMsg = _filterWord(word, filteredMsg)
            except Exception as error: # pylint: disable=broad-except
                print("Word Filter exception:")
                print(error)
                print(word)
                print(filteredMsg)
                print("==========")


        allFiltered = _isAllFiltered(filteredMsg)

        if filteredMsg == originalMsg:
            pass # no bad words, don't need to do anything else
        elif (filteredMsg != originalMsg and oneWord) or allFiltered:
            await self.bot.delete_message(msg) # delete message but don't show full message context
            filterNotify = "{0.author.mention} was filtered!".format(msg)
            notifyMsg = await self.bot.send_message(msg.channel, filterNotify)
            await asyncio.sleep(3)
            await self.bot.delete_message(notifyMsg)
        else:
            await self.bot.delete_message(msg)
            filterNotify = "{0.author.mention} was filtered! Message was: \n".format(msg)
            embed = discord.Embed(colour=random.choice(self.colours),
                                  description="{0.author.name}#{0.author.discriminator}: "
                                  "{1}".format(msg, filteredMsg))
            await self.bot.send_message(msg.channel, filterNotify, embed=embed)

def _filterWord(word, string):
    regex = r'\b{}\b'.format(word)

    # Replace the offending string with the correct number of stars.  Note that
    # this only considers the length of the first time an offending string is
    # found with the current regex.  It will replace every string found with
    # this regex with the number of stars corresponding to the first offending
    # string.

    try:
        number = len(re.search(regex, string, flags=re.IGNORECASE).group(0))
    except Exception: # pylint: disable=broad-except
        # Nothing to replace, return original string
        return string

    stars = '*'*number
    repl = "{0}{1}{0}".format('`', stars)
    return re.sub(regex, repl, string, flags=re.IGNORECASE)

def _isOneWord(string):
    return len(string.split()) == 1

def _isAllFiltered(string):
    words = string.split()
    cnt = 0
    for word in words:
        if bool(re.search("[*]+", word)):
            cnt += 1
    return cnt == len(words)

def setup(bot):
    """Add the cog to the bot."""
    checkFileSystem()
    wordFilterCog = WordFilter(bot)
    bot.add_listener(wordFilterCog.checkWords, 'on_message')
    bot.add_listener(wordFilterCog.checkWords, 'on_message_edit')
    bot.add_cog(wordFilterCog)
