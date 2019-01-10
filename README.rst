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
    pip install -e .


On discord, create a new app here:
https://discordapp.com/developers/applications/me/create

Also, click on "Create a Bot User" to generate a user for the bot, then get
the token associated to the bot. It will be useful for the bot's configuration.

Finally, you need to export an environment variable to pass the token to the
bot:

.. code-block:: bash

    export CACOPHONY_DISCORD_TOKEN=<YOUR_APP_TOKEN_HERE>

Last but not least, run the bot through:

.. code-block:: bash

    cacophony run

Congratulations! You're all set. Still, the bot itself hasn't that much
interest. You may install plugins then.


Contribute
----------

For any question as regard the bot, feel free to reach me on Ge0#1974
(Discord).


Roadmap
-------

- Add an automatic linter (flake8, isort).
- Write tests.
- Define a first plug-in architecture.
- Rewrite documentation.
- Lots of refactoring...
