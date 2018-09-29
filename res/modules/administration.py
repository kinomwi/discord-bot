from ..module import Module


# TODO: Method to delete messages from all channels at once
class Administration(Module):

    cmd_arg = 'mgmt'


    async def on_ready(self):
        
        # Clear channels
        for channel_id in self.bot.cfg.other['clear_channel_ids']:
            channel = self.bot.get_channel(channel_id)
            await self.clear_channel(channel)

        def_channel = self.bot.get_channel(self.bot.cfg.general['def_channel_id'])
        ready_msg = self.bot.cfg.other['ready_msg']

        # Send ready message
        if self.bot.cfg.other['ready_msg_toggle']:
            # Delete last ready message within 10 messages
            await self.delete_message_by_content(def_channel, ready_msg, 10, self.bot.user)

            await self.bot.send_message(def_channel, ready_msg)


    async def run(self, args=None, message=None):

        arg_fct_assoc = {
            'delete':       'delete',
            'dump_deleted': 'dump_delete_messages',
        }

        # Call function associated with second argument
        if message:
            if args:
                if args[0] in arg_fct_assoc.keys():
                    if len(args) >= 2 and not isinstance(args, str):
                        await getattr(self, arg_fct_assoc[args[0]])(args[1:], message)
                    else:
                        await getattr(self, arg_fct_assoc[args[0]])(None, message)
                else:
                    await self.bot.send_message(message.channel, "Command `" + args[0] + "` isn't available.")
                    await self.bot.run_module('help', [self.cmd_arg], message)
            else:
                await self.bot.run_module('help', [self.cmd_arg], message)
        else:
            await self.bot.run_module('help', [self.cmd_arg])


    async def return_help(self, args=None):
        return ("`delete last [n (max=200)] [optional: user-id] [optional: 'silent']`: Deletes the last n messages, optionally by a user, if the author has the appropriate rights. (The user-id can be copied by right-clicking on a user when in dev mode.)"
            "")


    # Executes different delete functions depending on third argument
    async def delete(self, args=None, message=None):

        arg_fct_assoc = {
            'last': 'delete_last_messages'
        }

        if args and message and len(args) >= 2 and not isinstance(args, str):
            if args[0] in arg_fct_assoc.keys():    # If command is registered
                await getattr(self, arg_fct_assoc[args[0]])(args[1:], message)
            else:
                await self.bot.send_message(message.channel, "Command `" + args[0] + "` isn't available.")
                await self.bot.run_module('help', [self.cmd_arg], message)
        else:
            await self.bot.run_module('help', [self.cmd_arg])



    # Deletes a specific number of messages, optionally by specific user
    #   1: limit, 2: user, 3: silent
    # TODO: Delete from all channels if additional argument 'global' is given (difficult)
    async def delete_last_messages(self, args, message):

        max_limit = 200

        limit = None
        user_id = None

        send_response = True
        silent_arg = 'silent'

        # server_wide = False
        # server_wide_arg = 'global'

        # Get arguments

        if isinstance(args, str):
            tmp_limit = args
        else:
            tmp_limit = args[0]

        if tmp_limit:
            tmp_limit = int(tmp_limit)
            if tmp_limit > max_limit:
                tmp_limit = max_limit
            limit = tmp_limit
        
        if not isinstance(args, str) and len(args) >= 2:

            if await self.bot.util.is_number(args[1]):
                user_id = args[1]

            if (silent_arg in i for i in args):
                send_response = False
            # if (server_wide_arg in i for i in args):
            #     server_wide = True
        

        # Delete messages
        if message.author.server_permissions.manage_messages or message.author.id == user_id:
            if limit:

                deleted_messages = []
                
                # By user
                if user_id:

                    tmp_limit = limit

                    def is_user(m):
                        return str(user_id) == str(m.author.id)

                    # Limit for purge function only applies to amount of messages checked, not deleted (TODO: Could be a bug that got fixed!)
                    # This loop repeats the purge function while increasing the amount of messages checked depending on how many messages were skipped
                    while len(deleted_messages) < limit and tmp_limit <= max_limit:
                        tmp_deleted_messages = await self.bot.purge_from(message.channel, limit=tmp_limit, check=is_user)
                        
                        deleted_messages += tmp_deleted_messages

                        amount_skipped = tmp_limit - len(tmp_deleted_messages)
                        tmp_limit = amount_skipped + limit - len(deleted_messages)

                    if send_response:
                        await self.bot.send_message(message.channel, "Deleted " + str(len(deleted_messages)) + " message(s) by " + user_id + ".")

                    if len(deleted_messages) > 0:
                        await self.dump_messages(deleted_messages)
                
                # Too many arguments
                elif len(args) > 2:
                    await self.bot.send_message("Too many arguments. Make sure to use the user-id, not the name of the user.")
                    await self.bot.run_module('help', self.cmd_arg)
                
                # By anyone
                else:
                    deleted_messages = await self.bot.purge_from(message.channel, limit=limit)

                    if send_response:
                        await self.bot.send_message(message.channel, "Deleted " + str(len(deleted_messages)) + " message(s).")

                    await self.bot.util.print("Deleted " + str(len(deleted_messages)) + " message(s) in " + message.channel.name + ".")
                    await self.dump_messages(deleted_messages)

            else:
                await self.bot.send_message(message.channel, "This command requires a limit.")
                await self.bot.run_module('help', self.cmd_arg)
        else: 
            await self.bot.send_message(message.channel, "User doesn't have permission to delete these messages.")
            await self.bot.run_module('help', [self.cmd_arg])


    # Deletes all messages within a channel
    # TODO: Check if more messages
    async def clear_channel(self, channel):
        deleted_messages = await self.bot.purge_from(channel, limit=200)
        if len(deleted_messages) > 0:
            await self.bot.util.print("Deleted " + str(len(deleted_messages)) + " message(s) in " + channel.name + ".")
            await self.dump_messages(deleted_messages)


    # Delete message by content
    async def delete_message_by_content(self, channel, content, search_limit=10, user=None):
        log = self.bot.logs_from(channel, limit=search_limit)
        async for msg in log:
            if msg.content == content:
                if user:
                    if msg.author == user:
                        await self.bot.delete_message(msg)
                else:
                    await self.bot.delete_message(msg)
                break


    async def dump_messages(self, messages):
        for msg in messages:
            name = str(msg.author)
            nick = ""
            if msg.author.nick:
                nick = " (" + msg.author.nick + ")"
            await self.bot.util.print("  " + name + nick + ": '" + msg.content + "'")


    '''# Counts all messages in the channel the command was sent in
    async def count_messages(self, message=None):
        counter = 0
        tmp = await client.send_message(message.channel, 'Calculating messages...')
        async for log in client.logs_from(message.channel, limit=1000):
            if log.author == message.author:
                counter += 1

        await client.edit_message(tmp, 'You have {} messages.'.format(counter))



    # Display a countdown with an optional event field
    # - `count-down [ss/mm:ss/hh:mm:ss] [optional: event name]`
    async def count_down(self, message=None):

        if message is not None:

            time_str = await self.bot.util.get_content_part(message.content, 2, 2)

            event_name = await self.bot.util.get_content_part(message.content, 3, 100)
            if event_name is None:
                event_name = ""
                event_name_until = ""
            else:
                event_name = "**"+event_name+"**"
                event_name_until = " until "+event_name

            time = await self.bot.util.time_str_to_sec(time_str)
            if time is not None:
                msg = await self.bot.util.send_message(message.channel, 'Counting: ')
                counter = time

                while counter > 0:
                    await self.bot.util.edit_message(msg, "Counting: " + await time_sec_to_str(counter) + event_name_until)
                    await asyncio.sleep(1)
                    counter -= 1

                await self.bot.util.edit_message(msg, 'Now! ' + event_name)

            else:
                await self.bot.util.help_message(message.channel, 'count-down')'''
    