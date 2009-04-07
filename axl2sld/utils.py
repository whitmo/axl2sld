from decorator import decorator
import sys

def arg_parser(optparser):
    @decorator
    def newfunc(func, args=None, options=None, parser=None):
        if args is None and options is None:
            argv = sys.argv
            options, args = optparser.parse_args(argv)
        return func(args, options, optparser)
    return newfunc
