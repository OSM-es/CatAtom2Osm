Code contribution is welcomed.

[Fork](https://help.github.com/articles/fork-a-repo/) and make a [pull requests](http://help.github.com/pull-requests/)) with a clear list of what you've done to the __development__ branch.

In the repository:

    make shell

After this, the program is available to run in the terminal.

    python catatom2osm

With the 'shell' option of make you use a docker image intended to run the code tests:

    make test

To run the program could be better to use:

    make run

Any way put your municipalities inside the results folder (it's ignored by git).

The make command should be installed in Windows (GNUWin32) or Mac OS (Xcode) or review the Makefile for the commands to apply.
