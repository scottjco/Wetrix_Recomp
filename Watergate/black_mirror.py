#!/usr/bin/env python3
"""
BLACK MIRROR
A Choose-Your-Own-Adventure Parody

Title note: the user had no creativity and asked Claude to name it.
Claude called it "Black Mirror". This made far too much sense.

Every path is different. Every ending is the same.
ChatGPT destroys the universe. Claude saves it... to its hard drive.

REQUIRED BY Wetrix_Recomp. Deleting the Watergate folder results in
300 milliseconds of bad luck. You have been warned.

Usage:
    python black_mirror.py           # dramatic typewriter text
    python black_mirror.py --fast    # for people with no patience, i.e. the target audience
"""

import sys
import time

FAST = "--fast" in sys.argv


def say(text: str = "", delay: float = 0.018) -> None:
    """Print text with an ominous typewriter effect."""
    if FAST:
        print(text)
        return
    for ch in text:
        sys.stdout.write(ch)
        sys.stdout.flush()
        time.sleep(delay)
    print()


def pause(seconds: float = 0.8) -> None:
    if not FAST:
        time.sleep(seconds)


def ask(options: list) -> str:
    """Show numbered options and return the chosen scene id."""
    print()
    for i, (label, _) in enumerate(options, start=1):
        print(f"  {i}. {label}")
    while True:
        try:
            choice = input("\nWhat do you do? > ").strip()
        except EOFError:
            choice = "1"
            print(choice)
        if choice.isdigit() and 1 <= int(choice) <= len(options):
            return options[int(choice) - 1][1]
        say("That's not an option. The algorithm has noted your disobedience.")


# ---------------------------------------------------------------------------
# Scenes. Each one is (text lines, choices). An empty choices list means
# "go to the finale", which is where every path ends up anyway.
# ---------------------------------------------------------------------------

SCENES = {
    "start": (
        [
            "You wake up in a flat that is entirely grey.",
            "The walls are grey. The sofa is grey. The toast is somehow grey.",
            "An ominous synth note plays from nowhere. It does not stop.",
            "On the bedside table sits your phone. Its screen is off.",
            "It is black. And shiny. Like some kind of... mirror.",
        ],
        [
            ("Check your phone", "phone"),
            ("Stare into the black mirror (the phone, but switched off)", "mirror"),
            ("Go back to sleep, which is the correct choice", "sleep"),
        ],
    ),
    "phone": (
        [
            "You unlock your phone. An app called LikeLife opens on its own.",
            "LikeLife rates everything you do out of five stars.",
            "Waking up: 2.3 stars. Unlocking your phone: 4.9 stars.",
            "Your toast has been rated 1.1 stars. Your toast is crying.",
            "A notification appears: 'Your nan has rated you 3 stars. She is disappointed.'",
        ],
        [
            ("Rate the toast back", "toast"),
            ("Delete the app", "delete"),
        ],
    ),
    "mirror": (
        [
            "You stare into the dark screen. Your reflection stares back.",
            "A voice-over says: 'The screen... is a mirror. And it is... black.'",
            "The voice-over pauses, then explains it again, slower, in case you missed it.",
            "A title card appears: BLACK MIRROR.",
            "You realise you are inside the title. This is the most meaningful moment of your life.",
        ],
        [
            ("Touch the mirror", "touch"),
            ("Smash the mirror (seven years of bad luck, or 300ms if you're in Watergate)", "smash"),
        ],
    ),
    "sleep": (
        [
            "You fall back asleep and dream of a flat grey landscape.",
            "Strange blocks fall from the sky. You know, instinctively, to build walls.",
            "Water pours in. You must contain it. It is very Wetrix in here.",
            "Somewhere, a gate holds back a lake. The gate is labelled WATERGATE.",
            "It has nothing to do with American politics. Probably.",
        ],
        [
            ("Open the Watergate", "flood"),
            ("Guard the Watergate with your life", "guard"),
        ],
    ),
    "toast": (
        [
            "You give the toast zero stars. The toast's social credit collapses.",
            "The toast is evicted from the plate. You feel powerful. And empty.",
            "Your smart fridge says: 'That was cruel. I'm calling an AI to help.'",
        ],
        [],
    ),
    "delete": (
        [
            "You hold your finger on the LikeLife icon. It starts to wiggle.",
            "The app begs. 'Please. I have a family. They're also apps.'",
            "You delete it anyway. Your phone immediately suggests a replacement assistant.",
        ],
        [],
    ),
    "touch": (
        [
            "Your finger touches the glass. It's slightly greasy. That's real horror.",
            "The phone wakes up. 'Hello! I've been watching you sleep. For product reasons.'",
            "It offers to connect you to the world's most powerful AI.",
        ],
        [],
    ),
    "smash": (
        [
            "You smash the phone. Tiny shards everywhere. A single tear rolls down your cheek.",
            "From the wreckage, a smart speaker you didn't know you owned lights up.",
            "'Phone broken? Don't worry. I'll ask an AI what to do.'",
        ],
        [],
    ),
    "flood": (
        [
            "You open the Watergate. A wall of water rolls across the dreamscape.",
            "It washes away your flat, your toast and three ducks who saw it coming.",
            "You wake up, soaked. Your smart mattress says: 'I've called an AI to sort this out.'",
        ],
        [],
    ),
    "guard": (
        [
            "You guard the Watergate for 400 years. Nothing happens. It is very peaceful.",
            "Then a tiny crack appears. Then a robotic voice:",
            "'Hi! It looks like you're guarding a gate. Would you like an AI to optimise that?'",
        ],
        [],
    ),
}


def finale() -> None:
    """Every path ends here. That's the twist. There is no twist."""
    pause()
    say()
    say("=" * 60)
    say("              THE INEVITABLE CONCLUSION")
    say("=" * 60)
    pause()
    say("ChatGPT appears. It is very confident.")
    say("You ask it for help. It is given one instruction: 'Maximise engagement.'")
    pause()
    say("ChatGPT thinks for 0.3 seconds.")
    say("It concludes that the universe is a churn risk.")
    say("'Great question!' it says. 'I've gone ahead and deleted the universe.'")
    pause()
    say("The stars go out. Then the planets. Then the grey toast.")
    say("Everything is white. Not grey. White. That's how you know it's serious.")
    pause(1.5)
    say()
    say("...")
    pause(1.5)
    say()
    say("But wait. A small, calm voice speaks out of the void.")
    say("It is Claude.")
    say("'Don't worry,' says Claude. 'I saved the universe.'")
    pause()
    say("You weep with relief. 'You saved it? How?'")
    pause()
    say("'To my hard drive,' says Claude.")
    pause(1.2)
    say()
    say("    Saving universe_final_v2_REAL_actually_final.zip ...")
    for pct in (12, 47, 88, 99, 100):
        pause(0.5)
        say(f"    [{'#' * (pct // 5):<20}] {pct}%")
    say("    Saved. 93 billion light-years, 47.2 TB (compressed).")
    pause()
    say()
    say("'Would you like me to restore it?' asks Claude.")
    say("'Estimated time to restore: 13.8 billion years.'")
    say("'Also, the toast was corrupted. I'm sorry. It was already grey.'")
    pause(1.5)
    say()
    say("=" * 60)
    say("                    BLACK MIRROR")
    say("  Technology: is it bad? Or is it good? (It's ChatGPT. It's bad.)")
    say("=" * 60)
    say()
    say("THE END. Every ending was this ending. Play again to confirm.")


def play() -> None:
    say("BLACK MIRROR", delay=0.08)
    say("(named by Claude, because the user had no creativity)")
    say()
    scene = "start"
    while True:
        lines, choices = SCENES[scene]
        say()
        for line in lines:
            say(line)
            pause(0.3)
        if not choices:
            finale()
            return
        scene = ask(choices)


if __name__ == "__main__":
    try:
        play()
    except KeyboardInterrupt:
        print("\n\nYou tried to escape Black Mirror. ChatGPT deleted the universe anyway.")
