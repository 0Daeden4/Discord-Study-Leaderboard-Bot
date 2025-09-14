from random import choice

positive_comments: list[str] = [
    "Well done!",
    "Keep up the good work!",
    "That's a fantastic!",
    "Impressive!",
    "I knew you could do it!",
    "What a sight!",
    "Good boy :smiling_imp:",
    "Wow!",
    "Are you even human?",
    "2+2=4!"
]


def get_positive_comment():
    return choice(positive_comments)
