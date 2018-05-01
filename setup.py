"""Setup File for Lilypond To Band Video Converter."""

from setuptools import setup, find_packages
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

#============================================================

setup(
    name = "LilypondToBandVideoConverter",
    version = "1.0rc1",
    description = "Generator for Notation Videos from Lilypond Text",
    long_description = long_description,
    #long_description_content_type = "text/markdown",
    url = "https://github.com/prof-spock/LilypondToBandVideoConverter",
    author = "Dr. Thomas Tensi",
    author_email = "t.tensi@gmx.de",
    license = "MIT",
    classifiers = [
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Multimedia :: Sound/Audio :: Conversion",
        "Topic :: Multimedia :: Video :: Conversion",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
    ],
    keywords = "video audio generation midi lilypond",
    package_dir = { "" : "src" },
    packages = find_packages("src"),
    install_requires = ["mutagen"],
    python_requires = ">=2.7, !=3.0.*, !=3.1.*, !=3.2.*, <4",
    data_files = [
        ("config", ["config/ltbvc-global.cfg"]),
        ("demo",   ["demo/test-music.ly", "demo/test-config.txt"]),
        ("doc",    ["lilypondToBandVideoConverter.pdf"])
    ],
    entry_points = { "console_scripts": [ "lilyToBVC=ltbvc:main" ] }
)
