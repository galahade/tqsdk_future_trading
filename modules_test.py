import argparse

parser = argparse.ArgumentParser(description="calculate X to the power of Y")

group = parser.add_mutually_exclusive_group()

# parser.add_argument("echo", help="echo the string you yse here")
# parser.add_argument("square", help="display a square of a given number",
#                    type=int)
# parser.add_argument("-v", "--verbosity",
                    # help="increase output verbosity", action="store_true")

# parser.add_argument("-v", "--verbosity", type=int, choices=[0, 1, 2],
#                     help="increase output verbosity")
# parser.add_argument("-v", "--verbosity", action="count",
#                    default=0, help="increase output verbosity")
group.add_argument("-q", "--quiet", action="store_true")
group.add_argument("-v", "--verbosity", action="store_true")
parser.add_argument("x", type=int, help="the base")
parser.add_argument("y", type=int, help="the exponent")
args = parser.parse_args()

# answer = args.square**2
answer = args.x**args.y
# if args.verbosity >= 2:
#     print(f"{args.x} to the power {args.y} equals {answer}")
# elif args.verbosity >= 1:
#     print(f"{args.x}^{args.y} == {answer}")
# else:
#     print(answer)
# if args.verbosity >= 2:
#     print(f"Running '{__file__}'")
# if args.verbosity >= 1:
#     print(f"{args.x}^{args.y} == {answer}")
# else:
#     print(answer)
if args.quiet:
    print(answer)
elif args.verbosity:
    print(f"{args.x} to the power {args.y} equals {answer}")
else:
    print(f"{args.x}^{args.y} == {answer}")



<em>Hello</em> world!
