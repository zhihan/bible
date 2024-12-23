""" A script to add verses to the message text."""

import argparse
import collections
import json
import logging
import os
import re
from typing import List, Optional, Sequence, Tuple
from urllib import parse, request


SCRIPTURE_READING = "Scripture Reading:"
VERSE_PATTERN = r"(([0-9] )?[A-Z][a-z]+\.? )?([0-9a-d:\-, ])+"
V_PATTERN = r"(v.|vv.) [0-9a-d\-, ]+"
URL = "https://api.lsm.org/recver.php?String={}&&Out=json"


def is_scripture_reading(line: str):
    return line.startswith(SCRIPTURE_READING)


def remove_trailing_punctuation(line: str) -> str:
    return line.strip().rstrip(".?!:,;")


def remove_words(maybe_ref: str) -> str:
    """Remove words that are not part of the reference."""
    maybe_ref = maybe_ref.replace("cf.", "").strip()
    if ", footnote" in maybe_ref:
        maybe_ref = maybe_ref.split(", footnote", 1)[0].strip()
    return maybe_ref


def is_reference(maybe_ref: str) -> bool:
    maybe_ref = remove_words(maybe_ref)
    return bool(re.fullmatch(VERSE_PATTERN, maybe_ref)) or bool(
        re.fullmatch(V_PATTERN, maybe_ref)
    )


def find_dash_before_reference(line: str) -> Optional[int]:
    """Find the dash before references.

    A reference can be added to the end of line with a dash separating
    them.

    Example:
       The Lord is the word of God. - John 1:1
    """
    line = remove_trailing_punctuation(line)
    if "-" not in line:
        return None
    # Try to parse the RHS of dash from left to right.
    dashes = re.finditer("-", line)
    for dash in dashes:
        maybe_verses = line[dash.start() + 1 :].strip()
        maybe_ref = maybe_verses.split("; ")
        logging.debug("Maybe a ref: %s", maybe_ref)
        if all(is_reference(verse) for verse in maybe_ref):
            logging.debug("Found a reference: %s", maybe_ref)
            return dash.start()
        else:
            logging.warning("Not a reference: %s", maybe_ref)
    return None


def find_references_in_paren(line: str) -> List[str]:
    """Find the references in parenthses

    A reference can be added inline with the text in parenthesis

    Example:
       The Lord is the word of God (John 1:1-2).
    """
    result = []
    for match in re.finditer(r"\(([^)]+)\)", line):
        logging.debug("Found paren: %s", match.group(1))
        in_paren = match.group(1).strip()
        maybe_ref = in_paren.split("; ")
        for a_maybe_ref in maybe_ref:
            if is_reference(a_maybe_ref):
                logging.debug("Found a reference in paren: %s", a_maybe_ref)
                result.append(a_maybe_ref)
            else:
                logging.warning("Not a reference in paren: %s", a_maybe_ref)
    if result:
        logging.debug("Found references in paren: %s", result)
    return result


def fetch_verse(verse_request: str) -> Sequence[Tuple[str, str]]:
    """Fetch a verse from LSM's verse requester API."""
    req = request.Request(
        URL.format(parse.quote(verse_request)), headers={"User-Agent": "Mozilla/5.0"}
    )
    logging.debug("Fetching: %s", req.full_url)
    result = []
    with request.urlopen(req) as response:
        content = response.read().decode("utf-8")
        response_json = json.loads(content)
        for verse in response_json["verses"]:
            if "No such verse in" in verse["text"]:
                # This usually happen if a inline reference is rely on the book and
                # chapter in the context. If that happens, the best way is to just
                # update the reference from abbreviated to a full reference.
                logging.error("No such verse in: %s PLEASE CHECK", verse_request)
            result.append((verse["ref"], verse["text"]))

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

            # If the reference is to the same book or chapter, sometimes the
            # reference will omit them.
            book = self.last_book
            chapter = self.last_chapter

            # Remove `cf.` and such, they are not part of the reference.
            stripped = remove_words(stripped)
            logging.debug("Processing reference: '%s'", stripped)
            if re.fullmatch(V_PATTERN, stripped):
                # Example: v. 1, vv. 1-3
                verse = stripped.split(" ", 1)[1]
            elif re.fullmatch(VERSE_PATTERN, stripped):
                # Either a full reference
                if " " in stripped:
                    book, chapter_and_verse = stripped.rsplit(" ", 1)
                else:
                    book = self.last_book
                    chapter_and_verse = stripped
                if ":" in chapter_and_verse:
                    chapter, verse = chapter_and_verse.split(":", 1)
                else:
                    chapter = self.last_chapter
                    verse = chapter_and_verse
            else:
                logging.error("Can't parse: '%s', ignoring.", item)
                continue
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
        elif ref_in_paren := find_references_in_paren(line):
            logging.debug("References in paren: %s", ref_in_paren)
            verses.extend(processer.process(ref_in_paren))
        out.append("")
        for verse in verses:
            out.append(f"{verse[0]}  {verse[1]}")
        out.append("")
    return out


if __name__ == "__main__":
    """Usage

    python3 add_verses.py <input-file.txt>

    The output will direct to stdout and logs go to stderr.
    If you need to save the output to a file, use

    python3 add_verses.py <input-file.txt> 1>/path/to/output.txt
    """
    parser = argparse.ArgumentParser(
        description="Process a file with scripture references."
    )
    parser.add_argument("file_name", type=str, help="The name of the file to process")
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.WARNING,
        format="%(filename)s:%(lineno)d: %(levelname)s - %(message)s",
    )
    out = process(args.file_name)
    print("\n".join(out))
