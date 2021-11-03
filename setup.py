"""Setup File for Lilypond To Band Video Converter."""

from setuptools import setup, find_packages
from os import path

here = path.abspath(path.dirname(__file__))

# version and root directories for installation and sources
installationVersion = "1.1"
installationRootDirectory = "Lib/site-packages/lilypondToBVC"
sourceRootDirectory = "lilypondtobvc/src"

with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

#============================================================

setup(
    name = "LilypondToBandVideoConverter",
    version = installationVersion,
    description = "Generator for Notation Videos from Lilypond Text",
    long_description = long_description,
    long_description_content_type = "text/markdown",
    url = "https://github.com/prof-spock/LilypondToBandVideoConverter",
    author = "Dr. Thomas Tensi",
    author_email = "t.tensi@gmx.de",
    license = "MIT",
    classifiers = [
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Multimedia :: Sound/Audio :: Conversion",
        "Topic :: Multimedia :: Video :: Conversion",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.7",
    ],
    keywords = "video audio generation midi lilypond",
    #package_dir = { "" : "" },
    packages = [sourceRootDirectory + "/basemodules",
                sourceRootDirectory + "/convertermodules"],
    install_requires = ["mutagen"],
    python_requires = ">=3.7, <4",
    data_files = [
        (installationRootDirectory, ["LICENSE.txt",
                                     "lilypondToBandVideoConverter.pdf"]),
        (installationRootDirectory + "/demo",
             ["demo/demo.jpg",
              "demo/wonderful_song-music.ly",
              "demo/globalconfig-pre.txt",
              "demo/globalconfig-post.txt",
              "demo/wonderful_song-config.txt"])
    ],
    entry_points = { "console_scripts":
        [ "lilypondToBVC=lilypondtobvc.src.convertermodules.ltbvc:main" ]
    }
)
