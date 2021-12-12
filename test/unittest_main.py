"""Entry point to run test with coverage.py"""

# copied directly from 2.7's unittest/__main__.py b/c coverage can't do -m


if __name__ == "__main__":
    import sys
    if sys.argv[0].endswith("__main__.py"):
        sys.argv[0] = "python -m unittest"

    __unittest = True

    from unittest.main import main, TestProgram#, USAGE_AS_MAIN
    #TestProgram.USAGE = USAGE_AS_MAIN
    main(module=None)
