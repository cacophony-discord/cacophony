Cacophony
=========

Cacophony is a modulable discord bot.


Installation
------------

At the moment, there is no package released on pypi.

Start by cloning the repository:

.. code-block:: bash

    git clone https://github.com/cacophony-discord/cacophony

Then `cd` into the directory and setup the bot:

.. code-block:: bash

    cd cacophony
    python setup.py install


On discord, create a new app here:
https://discordapp.com/developers/applications/me/create

Also, click on "Create a Bot User" to generate a user for the bot, then get
the token associated to the bot. It will be useful for the bot's configuration.

Create a new profile:

.. code-block:: bash

    cacophony create --profile mybot

Then go to `~/.config/cacophony-discord/mybot/config.yml` and replace the
`MY_TOKEN_HERE` string by your token.

Congratulations, you're all set!


Contribute
----------

You can join cacophony's discord server at https://discord.gg/G9xM8ux

Also, for any question as regard the bot, feel free to reach me on Ge0#1974.
