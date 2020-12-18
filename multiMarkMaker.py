#!/usr/bin/env python3

import sys
import email
import shlex
import subprocess
from subprocess import Popen, PIPE, STDOUT
from email.mime.text import MIMEText           # don't think I need this?
from email.mime.multipart import MIMEMultipart # don't think I need this?
from email.message import EmailMessage
from email.policy import EmailPolicy, default

def convert(cmd, text):
    pipe = Popen(cmd, stdout=PIPE, stdin=PIPE)
    body = pipe.communicate(input=text)[0]
    return body

def makeParts(message):
    bodyText = message.get_payload()

    # correct encoding
    if isinstance(bodyText, str):
        bodyText = bodyText.encode('utf-8')
    else:
        bodyText = message.get_payload(None, True)
        if not isinstance(bodyText, bytes):
            bodyText = bodyText.encode('utf-8')

    # basic asciidoctor command
    # (including adding my stylesheet)
    asciidoctorBaseCmd = ' '.join(['asciidoctor',
                                  '-a stylesdir=/home/hugo/.config/neomutt/styles',
                                  '-a stylesheet=personal.css',
                                  '-a source-highlighter=pygments',
                                  '-a last-update-label!', # disable 'last updated' label
                                  '-o -',
                                  '-'])

    # convert email body to html
    asciiDoctorHTMLCmd = shlex.split(asciidoctorBaseCmd)
    htmlBody = convert(asciiDoctorHTMLCmd, bodyText).decode('utf-8')
     
    # convert email body to docbook
    asciiDoctorDBCmd = shlex.split(' '.join([asciidoctorBaseCmd, '-b docbook']))
    docBookBody = convert(asciiDoctorDBCmd, bodyText)

    # convert docbook (from above) to markdown
    # (surely there is a python pandoc library?!)
    pandocCmd = shlex.split('pandoc -f docbook -t markdown')
    markDownBody = convert(pandocCmd, docBookBody).decode('utf-8')

    return (markDownBody, htmlBody)

def main():
    message = email.message_from_file(sys.stdin, policy=default)

    # this doesn't all take account of the filetypes...
    
    # get the markdown and html body part
    markDownBody, htmlBody = makeParts(message)

    # Make primary message of type text/plain
    # message.set_param('maintype', 'text', header='Content-Type')
    # message.set_param('subtype', 'plain', header='Content-Type')

    # make markdown the primary body
    message.set_content(markDownBody)

    # make it a multipart email and add the htmlBody
    # (add_alternative() converts non-multipart messages for you)
    message.add_alternative(htmlBody, subtype='html')

    # write back to stdout
    print(message)

main() 
