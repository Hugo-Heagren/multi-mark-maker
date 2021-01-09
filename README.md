# MultiMarkMaker

MultiMarkMaker is simple cli tool which converts plaintext emails written in lightweight markup languages into multi-part emails with an html component.

It was originally written just for Asciidoc, but uses pandoc, and so supports any markup language that pandoc can read from.

**This project is very alpha.
Use with caution, and please file issues when things don't work!**

## Installation

There is no packaging or clever installation at the moment.
Just clone the repo (or just download multiMarkMaker.py) file alone, put it somewhere in your `$PATH` and use it.

multiMarkmaker requires a working installation of [pandoc](https://pandoc.org/), and requires [asciidoctor](https://asciidoctor.org/) for asciidoc support.
(**N.B.** _asciidoctor_, _not_ asciidoc or any other asciidoc implementation)

## Usage

The assumed default is to read from stdin and write to stdout.
The file to read can be specified with `--infile` / `-i` and the file to write with `--outfile` / `-o`.
multi-mark-make assumes that it is reading an email file with an email header, not just a markup document.
(This is by design, there are plenty of markup-to-text tools out there already.)

`--in-format` / `-f` (think 'f for from') specifies the markup language the body of the original email was written in.
`--out-format` / `-t` ('t for to') is the markup language of the plaintext part of the multipart email. You might want to write in asciidoc, but have your plaintext part presented in commonmark.
Both options default to [commonmark](https://commonmark.org/).
If the informat and outformat are the same, no conversion with external tools will be done.

Various other options can be set of the commandline, and [configured](#configuration) in a config file.

To convert an email, just pipe it into the program with whatever options you want:

```
$ cat myEmail | path/to/multiMarkMaker.py -o destfile.eml
```

Of course this isn't very useful, because most people don't need or want to save emails locally. 
To send the email, pipe it into an email sending program, like [msmtp](https://marlam.de/msmtp/):

```
$ cat myEmail | path/to/multiMarkMaker.py | msmtp friend@example.com
```

### Usage with (neo)mutt
multiMarkMaker was written because I wanted to be able to write asciidoc emails in vim from neomutt, and just press send without needing any complex macros, or to build multipart emails.
Here's how to do that.
Heavily inspired by [this blog post](https://nosubstance.me/post/mutt-secret-sauce/).

Set `sendmail` in your neomuttrc to the path to a simple wrapper script:
```neomuttrc
set sendmail = "/home/hugo/.config/neomutt/sendmail"
```

Where sendmail is something like:
```
#!/bin/sh
/home/hugo/software/multiMarkMaker/multiMarkMaker.py --config-file /home/hugo/.config/neomutt/adocConfig.toml | msmtp "$@"
```
You might need something more complex depending on your msmtp settings.

[Configure msmtp](https://marlam.de/msmtp/msmtp.html#Configuration-files) (or whatever other mail sending program you use).

**Make sure to remove any smtp settings from your neomutt config**.
For some reason, neomutt ignores the `sendmail` variable if your leave these in.

## Configuration

The `--config-file` / `-c` option specifies an config file.
There is support for finding these files automatically, (e.g. in `$XDG_CONFIG_HOME`), but it is untested and buggy.
You are very welcome to look through the code and play with it, but for now it is recommended that you just specify a file on the commandline.

The format of the config file is [toml](https://toml.io/).

All commandline arguments specified above can be specified as keys (in their long form), with their values being set as on the commandline.
Commandline options override the config file. (for this reasons, `--infile` and `--outfile` can be manually set as `-` on the commandline to force stdin / stdout.)

### asciidoctor Configuration
You can also specify a table `asciidoctor-options`, which will control the behaviour of asciidoctor.
This can contain the following asciidoctor options:
* `failure-level`
* `safe`
* `trace`
* `template-engine`
* `source-dir`
* `safe-mode`
* `template-dir`
* `attribute`
* `doctype`
* `eruby`
* `section-numbers`
* `quiet`
* `require`
* `timings`

(other asciidoctor options are ignored because they might break things.)

Each of these will passed as an option to asciidoctor:
* as `--key` if the value is true. (use this for on / off options)
* as `--key!` if the value is false. (use this for on / off options)
* as `--key value` otherwise.

There are three subtables you can use too:
* `asciidoctor-options.attribute` is a table of key, value pairs, where each pair is passed:
  * as `--attribute=key` if the value is true.
  * as `--attribute=key!` if the value is false.
  * as `--attribute=key=value` otherwise.
* `asciidoctor-options.require` is used to specify asciidoc requires, but is buggy at the moment.
* `asciidoctor-options.template-dir` is used to specify asciidoc template dirs, but is buggy at the moment.

### Example
A config file might look something like this:

```toml
# My multiMarkMaker config file!

# General settings
in-format = "asciidoctor"
out-format = "markdown"

# Asciidoctor specific stuff
[asciidoctor-options]
  [asciidoctor-options.attribute]
  source-highlighter = "pygments"
  last-update-label = false
  stylesdir = "/path/to/dir"
  stylesheet = "myStyleSheet.css"
```

## Credit
Credit to @oblitum, as this is inspired by [MIMEbellish](https://gist.github.com/oblitum/6eeffaebd9a4744e762e49e6eb19d189#file-mimembellish).
