""" A script to add verses to the message text."""

import argparse
import collections
import json
import logging
import os
import re
from typing import List, Optional, Tuple
from urllib import parse, request


SCRIPTURE_READING = "Scripture Reading:"
VERSE_PATTERN = r"(([0-9] )?[A-Z][a-z]+\.? )?[0-9:,\- ]+"
URL = "https://api.lsm.org/recver.php?String={}&&Out=json"


def is_scripture_reading(line: str):
    return line.startswith(SCRIPTURE_READING)


def remove_trailing_punctuation(line: str) -> str:
    return line.strip().rstrip(".?!:")


def find_dash_before_reference(line: str) -> Optional[int]:
    line = remove_trailing_punctuation(line)
    if "-" not in line:
        return None
    # Try to parse the RHS of dash from left to right.
    dashes = re.finditer("-", line)
    for dash in dashes:
        maybe_verses = line[dash.start() + 1 :].strip()
        maybe_ref = maybe_verses.split("; ")
        logging.debug("Maybe a ref: %s", maybe_ref)
        if all(re.fullmatch(VERSE_PATTERN, verse) for verse in maybe_ref):
            logging.debug("Found a reference: %s", maybe_verses)
            return dash.start()
    return None


def fetch_verse(verse_request: str) -> List[Tuple[str, str]]:
    req = request.Request(
        URL.format(parse.quote(verse_request)), headers={"User-Agent": "Mozilla/5.0"}
    )
    logging.debug("Fetching: %s", req.full_url)
    result = ["UNKNOWN"]
    with request.urlopen(req) as response:
        content = response.read().decode("utf-8")
        response_json = json.loads(content)
        result = [(verse["ref"], verse["text"]) for verse in response_json["verses"]]
    return result


class ScriptureProcesser:
    """Process a scripture, remembering the last book and chapter.

    Sometimes the reference will omit the last book and chapter, in which
    case we will use the last one.
    """

    def __init__(self):
        self.last_book = None
        self.last_chapter = None

    def _process_item(self, references: str) -> List[Tuple[str, str]]:
        # One item can be joined by ','.
        result = []
        items = references.split(",")
        for item in items:
            stripped = item.strip()
            if not stripped:
                continue
            if " " in stripped:
                book, chapter_and_verse = stripped.split(" ", 1)
            else:
                book = self.last_book
                chapter_and_verse = stripped
            if ":" in chapter_and_verse:
                chapter, verse = chapter_and_verse.split(":", 1)
            else:
                chapter = self.last_chapter
                verse = chapter_and_verse
            logging.debug(f"Fetching verse: {book} {chapter}:{verse}")
            verses = fetch_verse(f"{book} {chapter}:{verse}")
            result.extend(verses)
            self.last_book = book
            self.last_chapter = chapter
        return result

    def process(self, scriptures: List[str]) -> List[Tuple[str, str]]:
        result = []
        for scripture in scriptures:
            result.extend(self._process_item(scripture))
        return result


def process(file_name: str) -> List[str]:
    current_dir = os.getcwd()
    with open(os.path.join(current_dir, file_name)) as f:
        lines = f.readlines()

    processer = ScriptureProcesser()
    logging.debug("Read %d lines", len(lines))
    out = []
    for line in lines:
        if not line.strip():
            continue
        out.append(line)
        verses = []
        if is_scripture_reading(line):
            scriptures = line.split(SCRIPTURE_READING)[1].strip().split(";")
            scriptures = [verse.strip() for verse in scriptures]
            logging.debug("Scriptures: %s", scriptures)
            verses.extend(processer.process(scriptures))
        elif (dash := find_dash_before_reference(line)) is not None:
            scriptures = line[(dash + 1) :].strip()
            scriptures = remove_trailing_punctuation(scriptures)
            scriptures = scriptures.split(";")
            scriptures = [verse.strip() for verse in scriptures]
            verses.extend(processer.process(scriptures))

        out.append("")
        for verse in verses:
            out.append(f"{verse[0]}  {verse[1]}")
        out.append("")
    return out


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Process a file with scripture references."
    )
    parser.add_argument("file_name", type=str, help="The name of the file to process")
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(filename)s:%(lineno)d: %(levelname)s - %(message)s",
    )
    out = process(args.file_name)
    print("\n".join(out))
