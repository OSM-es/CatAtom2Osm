Code contribution is welcomed.

[Fork](https://help.github.com/articles/fork-a-repo/) and make a [pull requests](http://help.github.com/pull-requests/)) with a clear list of what you've done to the __development__ branch.

In the repository:

    make shell

After this, you are inside a docker container. The program is available to run in the terminal.

    catatom2osm

To run the code tests:

    make test

To run the program could be better to use 'run' instead of 'shell':

    make run

This way, you put your municipalities inside /catastro folder ($home). It's linked to the host results folder and ignored by git.

The make command should be installed in Windows (GNUWin32) or Mac OS (Xcode) or review the Makefile for the commands to apply.

To run code styling on each commit, install in your host https://pre-commit.com/

    pip install pre-commit
    pre-commit install

If you update existing user-facing strings or add new ones, you can translate them following this procedure. First, enter the docker container:

    make shell

Then, generate the translation files:

    make msg

You can now edit the modified files; e.g., `locale/po/es/LC_MESSAGES/catatom2osm.po`. After you're done, compile the translations once again from the shell:

    make msg

A tutorial is available here https://asciinema.org/a/459636
