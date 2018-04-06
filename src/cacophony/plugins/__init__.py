"""Cacophony plugins submodule.

A plugin may export several components:

  - Commands: can be executed by the users to expect some custom behaviour.
  - Hooks: can be triggered upon discords events (messages, bot answering) and
        performing custom operations.
  - Jobs: those are coroutines that will be scheduled besides the bot main
        loop.
  - Operations: basically, those are sub-commands that can be added to
        cacophony's command line. The term "operation" has been chosen in
        order not to collide with 'commands' that refers to the bot commands
        executable by the users on the discord. The operations refers to
        cli (Command Line Interface) custom sub-commands.

"""
