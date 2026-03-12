# Command line usage

_**PLEASE NOTE:** This page was copied from the_ [_equivalent page_](https://musescore.org/en/handbook/3/command-line-options) _in the MuseScore 3 Handbook. If you find an option that no longer works in MuseScore 4, please report it on GitHub and add a note next to that option on this page. If the option was intentionally removed from MuseScore 4 then please delete it from this page._

MSCORE(1) — General Commands Manual Page

### NAME

**mscore**, **MuseScore4** — MuseScore 4 sheet music editor

### SYNOPSIS

You can launch MuseScore from the command line by typing

-   `mscore [options] [filename …]` (Mac and Linux/BSD/Unix)
-   `musescore [options] [filename …]` (Linux/BSD/Unix)
-   `mscore4portable [options] [filename …]` (Linux AppImage)
-   `MuseScore4.exe [options] [filename …]` (Windows)

`[options]` and `[filename]` are optional. For this to work the MuseScore executable must be in `%PATH%` (Windows) resp. `$PATH` (Mac and Linux). If it is not, see [Revert to factory settings](https://musescore.org/en/handbook/3/revert-factory-settings#Via-command-line) for detailed instructions on how and where to find and execute the MuseScore executable from the command line on the various supported platforms.

A more detailed synopsis follows:

**mscore** \[**-deFfhIiLmnOPRstvw**]\
\[**-b** | **--bitrate** _bitrate_]\
\[**-c** | **--config-folder** _pathname_]\
\[**-D** | **--monitor-resolution** _DPI_]\
\[**-d** | **--debug**]\
\[**-E** | **--install-extension** _extension file_]\
\[**-e** | **--experimental**]\
\[**-F** | **--factory-settings**]\
\[**-f** | **--force**]\
\[**-h** | **-?** | **--help**]\
\[**-I** | **--dump-midi-in**]\
\[**-i** | **--load-icons**]\
\[**-j** | **--job** _file.json_]\
\[**-L** | **--layout-debug**]\
\[**-M** | **--midi-operations** _file_]\
\[**-m** | **--no-midi**]\
\[**-n** | **--new-score**]\
\[**-O** | **--dump-midi-out**]\
\[**-o** | **--export-to** _file_]\
\[**-P** | **--export-score-parts**]\
\[**-p** | **--plugin** _name_]\
\[**-R** | **--revert-settings**]\
\[**-r** | **--image-resolution** _DPI_]\
\[**-S** | **--style** _style_]\
\[**-s** | **--no-synthesizer**]\
\[**-T** | **--trim-image** _margin_]\
\[**-t** | **--test-mode**]\
\[**-v** | **--version**]\
\[**-w** | **--no-webview**]\
\[**-x** | **--gui-scaling** _factor_]\
\[**--diff**]\
\[**--long-version**]\
\[**--no-fallback-font**]\
\[**--raw-diff**]\
\[**--run-test-script**]\
\[**--score-media**]\
\[**--score-meta**]\
\[**--highlight-config**]\
\[**--score-parts**]\
\[**--score-parts-pdf**]\
\[**--score-transpose**]\
\[**--sound-profile**]\
\[**--source-update**]\
\[**--template-mode**]\
\[_file ..._]

### DESCRIPTION

**MuseScore** is a Free and Open Source WYSIWYG cross-platform multi-lingual music composition and notation software, released under the GNU General Public Licence (GPLv3).

Running **mscore** without any extra options launches the full graphical MuseScore program and opens any files specified on the command line.

The options are as follows:

-   **-b** | **--bitrate** _bitrate_

    Set MP3 output bitrate in kbit/s

-   **-c** | **--config-folder** _pathname_

    Override configuration and settings directory

-   **-D** | **--monitor-resolution** _DPI_

    Specify monitor resolution (override autodetection)

-   **-d** | **--debug**

    Start MuseScore in debug mode

-   **-E** | **--install-extension** _extension file_

    Install an extension file; soundfonts are loaded by default unless **-e** is also specified

-   **-e** | **--experimental**

    Enable experimental features, such as [layers](https://musescore.org/en/handbook/3/layer-experimental-0)

-   **-F** | **--factory-settings**

    Use only the standard built-in presets (“factory settings”) and delete user preferences; compare with the **-R** option (see also [Revert to factory settings](https://musescore.org/en/node/278582))

-   **-f** | **--force**

    Ignore score corruption and version mismatch warnings in “converter mode”

-   **-h** | **-?** | **--help**

    Display an overview of invocation instructions (doesn’t work on Windows)

-   **-I** | **--dump-midi-in**

    Display all MIDI input on the console

-   **-i** | **--load-icons**

    Load icons from the filesystem; useful if you want to edit the MuseScore icons and preview the changes

-   **-j** | **--job** _file.json_

    Process a conversion job (see [_EXAMPLES_](#examples) below)

-   **-L** | **--layout-debug**

    Start MuseScore in layout debug mode

-   **-M** | **--midi-operations** _file_

    Specify MIDI import operations file (see [_EXAMPLES_](#examples) below)

-   **-m** | **--no-midi**

    Disable MIDI input

-   **-n** | **--new-score**

    Start with the New Score wizard regardless whether it’s enabled or disabled in the user preferences

-   **-O** | **--dump-midi-out**

    Display all MIDI output on the console

-   **-o** | **--export-to** _file_

    Export the given (or currently opened) file to the specified output _file_. The file type depends on the extension of the filename given. This option switches to “converter mode” and avoids the graphical user interface.

-   **-P** | **--export-score-parts**

    When converting to PDF with the **-o** option, append each part’s pages to the created PDF file. If the score has no parts, all default parts will temporarily be generated automatically.

-   **-p** | **--plugin** _name_

    Execute the named plugin

-   **-R** | **--revert-settings**

    Use only the standard built-in presets (“factory settings”) but do not delete user preferences; compare with the **-F** option

-   **-r** | **--image-resolution** _DPI_

    Set image resolution for conversion to PNG files. Default: 300 DPI (actually, the value of “Resolution” of the PNG option group in the [Export tab of the preferences](https://musescore.org/en/node/278648#export))

-   **-S** | **--style** _style_

    Load a style file first; useful for use with the **-o** option

-   **-s** | **--no-synthesizer**

    Disable the integrated software synthesizer

-   **-T** | **--trim-image** _margin_

    Trim exported PNG and SVG images to remove whitespace surrounding the score. The specified _margin_, in pixels, will be retained (use `0` for a tightly cropped image). When exporting to SVG, this option only works with single-page scores.

-   **-t** | **--test-mode**

    Set test mode flag for all files, includes **--template-mode**

-   **-v** | **--version**

    Display the name and version of the application without starting the graphical user interface (doesn’t work on Windows)

-   **-w** | **--no-webview**

    Disable the web view component in the Start Center

-   **-x** | **--gui-scaling** _factor_

    Scale the score display and other GUI elements by the specified _factor_; intended for use with high-resolution displays

-   **--diff**

    Print a conditioned diff between the given scores

-   **--long-version**

    Display the full name, version and git revision of the application without starting the graphical user interface (doesn’t work on Windows)

-   **--no-fallback-font**

    Don’t use Bravura as fallback musical font

-   **--raw-diff**

    Print a raw diff between the given scores

-   **--run-test-script**

    Run script tests listed in the command line arguments

-   **--score-media**

    Export all media (except MP3) for a given score as a single JSON document to stdout

-   **--highlight-config**

    Set highlight to svg, generated from a given score

-   **--score-meta**

    Export score metadata to JSON document and print it to stdout

-   **--score-parts**

    Generate parts data for the given score and save them to separate mscz files

-   **--score-parts-pdf**

    Generate parts data for the given score and export it as a single JSON document to stdout

-   **--score-transpose**

    Transpose the given score and export the data to a single JSON file, print it to stdout

-   **--sound-profile** _sound-profile_

    Use with '-o .mp3' or with '-j ', override the sound profile in the given score(s).\
    Possible values: "MuseScore Basic", "Muse Sounds"

-   **--source-update**

    Update the source in the given score

-   **--template-mode**

    Save files in template mode (e.g. without page sizes)

MuseScore also supports the [automatic Qt command line options](http://doc.qt.io/qt-5/qguiapplication.html#supported-command-line-options).

### Batch conversion job JSON format

The argument to the **-j** option must be the pathname of a file comprised of a valid JSON document honoring the following specification:

-   The top-level element must be a JSONArray, which may be empty.
-   Each array element must be a JSONObject with the following keys:
    -   `in`: Value is the name of the input file (score to convert), as JSONString.
    -   `plugin`: Value is the filename of a plugin (with the `.qml` extension), which will be read from either the global or per-user plugin path and executed before the conversion output happens, as JSONString. Optional, but at least one of `plugin` and `out` _must_ be given.
    -   `out`: Value is the conversion output target, as defined below. Optional, but at least one of `plugin` and `out` _must_ be given.
-   The conversion output target may be a filename (with extension, which decided the format to convert to), as JSONString.
-   The conversion output target may be a JSONArray of filenames as JSONString, as above, which will cause the score to be written to multiple output files (in multiple output formats) sequentially, without being closed, re-opened and re-processed in between.
-   If the conversion output target is a JSONArray, one or more of its elements may also be, each, a JSONArray of two JSONStrings (called first and second half in the following description). This will cause part extraction: for each such two-tuple, all extant parts of the score will be saved _individually_, with filenames being composed by concatenating the first half, the name (title) of the part, and the second half. The resulting string must be a valid filename (with extension, determining the output format). If a score has no parts (excerpts) defined, this will be silently ignored without error.
-   Valid file extensions for output are:

    -   `flac`

        Free Lossless Audio Codec (compressed audio)

    -   `metajson`

        various score metadata (JSON)

    -   `mid`

        standard MIDI file

    -   `midi`

        standard MIDI file

    -   `mlog`

        internal file sanity check log (JSON)

    -   `mp3`

        MPEG Layer III (lossy compressed audio)

    -   `mpos`

        measure positions (XML)

    -   `mscx`

        uncompressed MuseScore file

    -   `mscz`

        compressed MuseScore file

    -   `musicxml`

        uncompressed MusicXML file

    -   `mxl`

        compressed MusicXML file

    -   `ogg`

        OGG Vorbis (lossy compressed audio)

    -   `pdf`

        portable document file (print)

    -   `png`

        portable network graphics (image) — Individual files, one per score page, with a hyphen-minus followed by the page number placed before the file extension, will be generated.

    -   `spos`

        segment positions (XML)

    -   `svg`

        scalable vector graphics (image)

    -   `wav`

        RIFF Waveform (uncompressed audio)

    -   `xml`

        uncompressed MusicXML file

See below for an example.

### ENVIRONMENT

-   `SKIP_LIBJACK`

    Set this (the value does not matter) to skip initialization of the JACK Audio Connection Kit library, in case it causes trouble.

-   `XDG_CONFIG_HOME`

    User configuration location; defaults to `~/.config` if unset.

-   `XDG_DATA_HOME`

    User data location; defaults to `~/.local/share` if unset.

Note that MuseScore also supports the normal Qt environment variables such as `QT_QPA_GENERIC_PLUGINS`, `QT_QPA_PLATFORM`, `QT_QPA_PLATFORMTHEME`, `QT_QPA_PLATFORM_PLUGIN_PATH`, `QT_STYLE_OVERRIDE`, `DISPLAY`, etc.

### FILES

`/usr/share/mscore-4.0/` contains the application support data (demos, instruments, localization, system-wide plugins, soundfonts, styles, chords, templates and wallpapers). In the Debian packages, system-wide soundfonts are installed into `/usr/share/sounds/sf2/`, `/usr/share/sounds/sf3/` or `/usr/share/sounds/sfz/`, respectively, instead.

The per-user data (extensions, plugins, soundfonts, styles, templates) and files (images, scores) are normally installed into subdirectories under `~/MuseScore4/` but may be changed in the configuration. Note that snapshot, alpha and beta versions use `MuseScore4Development` instead of `MuseScore4` in all of these paths.

`$XDG_CONFIG_HOME/MuseScore/MuseScore4.ini` contains the user preferences, list of recently used files and their locations, window sizes and positions, etc. See above for development version paths.

`$XDG_DATA_HOME/data/MuseScore/MuseScore4/` contains updated localization files downloaded from within the program, plugin information, cached scores, credentials for the _musescore.com_ community site, session information, synthesizer settings, custom key and time signatures and shortcuts. See above for development version paths.

### EXAMPLES

#### Convert a score to PDF from the command line

```
mscore -o 'My Score.pdf' 'My Score.mscz'
```

#### Run a batch job converting multiple documents

```
mscore -j job.json
```

This requires assumes a file `job.json` exists in the current working directory with content similar to the following:

```
[
    {
        "in": "MyScore1.mscz",
        "out": "MyScore1.pdf"
    },
    {
        "in": "MyScore2.mscz",
        "plugin": "colornotes.qml",
        "out": [
            "MyScore2-notecolors.pdf",
            "MyScore2-notecolors.svg"
        ]
    },
    {
        "in": "MyScore3.mscz",
        "out": [
            "MyScore3.pdf",
            "MyScore3.musicxml",
            "MyScore3.mid",
            [
                "MyScore3 (",
                " part).pdf"
            ]
        ]
    }
]
```

If `MyScore3.mscz` contains excerpts (instrumental parts) then the syntax above would cause files like “`MyScore3 (Violin part).pdf`” to be generated alongside the conductor’s PDF and MusicXML files, as well as a MIDI file with the full orchestral sound. If `MyScore3.mscz` has no excerpts defined then only the conductor’s PDF, MusicXML, and orchestral MIDI files will be generated, while the request for part PDFs is silently ignored.

#### MIDI import operations

The attached [`midi_import_options.xml`](https://musescore.org/sites/musescore.org/files/midi_import_options_0.xml) is a sample MIDI import operations file for the **-M** option.

### DIAGNOSTICS

The **mscore** utility exits 0 on success, and >0 if an error occurs.

### SEE ALSO

fluidsynth(1), midicsv(1), timidity(1), qtoptions(7)

-   [_https://musescore.org/handbook_](https://musescore.org/handbook)

    Online Handbook, full user manual

-   [_https://musescore.org/forum_](https://musescore.org/forum)

    Support Forum

-   [_https://musescore.org/en/node/278582_](https://musescore.org/en/node/278582)

    Reverting to factory settings (troubleshooting)

-   [_https://github.com/musescore/MuseScore/issues_](https://github.com/musescore/MuseScore/issues)

    Project Issue Tracker — Please check first to if the bug you’re encountering has already been reported. If you just need help with something, then please use the [support forum](https://musescore.org/forum) instead.

-   [_http://doc.qt.io/qt-5/qguiapplication.html#supported-command-line-optio…_](http://doc.qt.io/qt-5/qguiapplication.html#supported-command-line-options)

    Documentation of automatic Qt command line options

### STANDARDS

MuseScore attempts to implement the following standards:

-   MusicXML 3.1 (score interchange format)
-   SF2 (SoundFont 2.01)
-   SF3 (SoundFont with OGG Vorbis-compressed samples)
-   SFZ (Sforzato soundfont)
-   SMuFL (Standard Music Font Layout 1.20)

### HISTORY

MuseScore was split off the MusE sequencer in 2002 and has since become the foremost Open Source notation software.

### AUTHORS

MuseScore is developed by **MuseScore BVBA** and others.

This manual page was written by _mirabilos_ <[tg@debian.org](mailto:tg@debian.org)>.

### CAVEATS

The automatic Qt command line options are removed from the argument vector before the application has a chance at option processing; this means that an invocation like `mscore -S -reverse` has no chance at working because the `-reverse` is removed by Qt first.

### BUGS

-   MuseScore Studio does not honor _/etc/papersize_.
-   Probably some more; check the project’s bug tracker (cf. [_SEE ALSO_](#see-also)).
