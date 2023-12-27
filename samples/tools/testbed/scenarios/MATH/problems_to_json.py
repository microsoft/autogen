import json

problems = [
    "Find all $x$ that satisfy the inequality $(2x+10)(x+3)<(3x+9)(x+8)$. Express your answer in interval notation.",
    "Find the value of $a_2+a_4+a_6+a_8+\\dots+a_{98}$ if $a_1, a_2, a_3, \\ldots$ is an arithmetic progression with common difference $1$ and \\[a_1+a_2+a_3+\\dots+a_{98}=137.\\]",
    "Tina the tourist goes on a trip. She starts at the origin and drives north (in the positive $y$ direction) for $10$ units. Then she turns east (the positive $x$ direction) and as she's turning her camera flies out the window and lands exactly at $(0,10)$. She then drives $9$ units east, turns and drives $8$ units north.  She continues this pattern of turning and driving one unit less than after the previous turn, until stopping after driving $1$ unit east. She reaches for her camera only to find it missing! She activates the GPS homing device on her camera and drives back to it in a straight line. What is the equation of this line? Express your answer as $ax+by=c$, where $a$, $b$, and $c$ are integers, $a>0$, and $a$ is as small as possible.",
    "For what negative value of $k$ is there exactly one solution to the system of equations \\begin{align*}\ny &= 2x^2 + kx + 6 \\\\\ny &= -x + 4?\n\\end{align*}",
    "If $\\frac{3x^2-4x+1}{x-1}=m$, and $x$ can be any real number except $1$, what real values can $m$ NOT have?",
    "Find all numbers $a$ for which the graph of $y=x^2+a$ and the graph of $y=ax$ intersect. Express your answer in interval notation.",
    "If $\\displaystyle{f(x)=x^{(x+1)}(x+2)^{(x+3)}}$, then find the value of $f(0)+f(-1)+f(-2)+f(-3)$.",
    "An envelope contains eight bills: 2 ones, 2 fives, 2 tens, and 2 twenties. Two bills are drawn at random without replacement. What is the probability that their sum is $\\$20$ or more?",
    "Find the coefficient of $x^2$ in the expansion of the product $$(1-x)(1+2x)(1-3x)\\dotsm(1+14x)(1-15x).$$",
    "All 50 states as well as the District of Columbia and Puerto Rico, have distinct two-letter postal abbreviations. If a two-letter sequence of letters (such as CO or EE) is chosen at random, what is the probability that it is a postal abbreviation for one of the 50 states, the District of Columbia, or Puerto Rico? Express your answer as a common fraction.",
    "Let $x$ and $y$ be real numbers.  Find the set of possible values of\n\\[\\frac{(x + y)(1 - xy)}{(1 + x^2)(1 + y^2)}.\\]",
    "On a number line, the coordinates of $P$ and $Q$ are 8 and 48, respectively. The midpoint of $\\overline{PQ}$ is $B$, the midpoint of $\\overline{BQ}$ is $C$, and the midpoint of $\\overline{PC}$ is $D$. What is the coordinate of $D$?",
    "Find $24^{-1} \\pmod{11^2}$. That is, find the residue $b$ for which $24b \\equiv 1\\pmod{11^2}$.\n\nExpress your answer as an integer from $0$ to $11^2-1$, inclusive.",
    "There are two cameras that take pictures of a traffic intersection. Camera A starts taking pictures at $6$ AM and takes a picture every $11$ minutes. Camera B starts taking pictures at $7$ AM and takes pictures every $7$ minutes. Camera A and Camera B take a picture at the same time at four different times before noon. When Camera A and Camera B take their last picture together, how many minutes before noon is it?",
    "Let $z$ be a complex number such that $z^{13} = 1.$  Let $w_1,$ $w_2,$ $\\dots,$ $w_k$ be all the possible values of\n\\[z + z^3 + z^4 + z^9 + z^{10} + z^{12}.\\]Find $w_1^2 + w_2^2 + \\dots + w_k^2.$",
    "There are 190 people on the beach. 110 are wearing sunglasses, 70 are wearing bathing suits, and 95 are wearing a hat.  Everyone is wearing at least one of these items. 30 are wearing both bathing suits and sunglasses. 25 are wearing both bathing suits and a hat. 40 are wearing both sunglasses and a hat.  How many people are wearing all three items?",
    "Completely simplify and rationalize the denominator: $$\\frac{\\sqrt{160}}{\\sqrt{252}}\\times\\frac{\\sqrt{245}}{\\sqrt{108}}$$",
]
answers = [
    # 6 algebra
    "(-\\infty, -14)\\cup(-3,\\infty)",
    "93",
    "4x-5y=-50",
    "-5",
    "2",
    "(-\\infty,0]\\cup[4,\\infty)",
    # 11 problems, 2 from each category, (1 algebra is deleted)
    "\\frac{10}{9}",
    "\\frac{1}{2}",
    "-588",
    " \\frac{1}{13}",
    "\\left[ -\\frac{1}{2}, \\frac{1}{2} \\right]",
    "23",
    "116",
    "41",
    "43",
    "10",
    "\\frac{5\\sqrt{42}}{27}",
]


def problem_to_json():
    with open("problems.jsonl", "w") as f:
        for i, problem in enumerate(problems):
            # a = {
            #     'id': problem{i}',
            #     'template': 'scenario.py',
            #     'substitutions': {
            #         '__PROMPT__': problem,
            #         '__ANSWER__': answers[i],
            #     },
            # }
            a = {
                "id": f"problem{i}",
                "template": "./",
                "substitutions": {"prompt.txt": {"__PROMPT__": problem}, "answer.txt": {"__ANSWER__": answers[i]}},
            }
            # Convert the dictionary to a JSON string and write it to the file
            json_string = json.dumps(a)
            f.write(json_string + "\n")  # Add a newline character after each JSON object


problem_to_json()

problems = []
with open("problems.jsonl", "r") as file:
    for line in file:
        # Parse each line as a JSON object
        problem = json.loads(line)
        problems.append(problem)
        print(problem["substitutions"])
        print()

# Now 'problems' is a list of dictionaries, each representing a problem
