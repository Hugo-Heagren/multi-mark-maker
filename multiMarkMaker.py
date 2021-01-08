#!/usr/bin/env python3

import argparse
import sys
import toml
import os
import os.path
import itertools
import shlex
from collections import OrderedDict
import subprocess
from subprocess import Popen, PIPE, STDOUT
import email
from email.message import EmailMessage ,MIMEPart
from email.policy import EmailPolicy, default


class Setting():
    def __init__(self, longName=None, shortName=None, value=None, cli=True, confFile=True):
      self.longName  = longName
      self.shortName = shortName
      self.cli       = cli        # whether an option may be specified on the cli
      self.confFile  = confFile   # whether an option may be specified in the config file
      self.value     = value      # also the default value

def declareSettings():
    settings = {
            'asciidoctor_options':        Setting(longName='asciidoctor-options',                       value='', cli=False),
            'asciidoctor_options_string': Setting(longName='asciidoctor-options-string', shortName='a', value='', confFile=False),
            'infile':                     Setting(longName='infile',                     shortName='i', value='-'),
            'outfile':                    Setting(longName='outfile',                    shortName='o', value='-'),
            'out_format':                 Setting(longName='out-format',                 shortName='t', value='commonmark'),
            'config_file':                Setting(longName='config-file',                shortName='c', value=''), # this needs to be stored with an os.expandvars, so that '~' etc. work
            'attach_file_references':     Setting(longName='attach-file-references',     shortName='r', value=True),
            'attach_inline_code':         Setting(longName='attach-inline-code',         shortName='l', value=False), # make and attach files out of all hard-written code snippets
            'in_format':                  Setting(longName='in-format',                  shortName='f', value='commonmark')
            }
    return settings

isAllowedAdoc = {
    'failure-level': True,
    'safe': True,
    'trace': True,
    'base-dir': False,
    'destination-dir': False,
    'template-engine': True,
    'load-path': False,
    'source-dir': True,
    'safe-mode': True,
    'template-dir': True,
    'version': False,
    'attribute': True,
    'backend': False,
    'doctype': True,
    'eruby': True,
    'help': False,
    'section-numbers': True,
    'out-file': False,
    'quiet': True,
    'require': True,
    'no-header-footer': False,
    'timings': True,
    'verbose': False
    }

# takes a dictionary of Setting objects and return a parser for parsing them
# out of cli args
def makeParser(settings):
    parser = argparse.ArgumentParser(description='Convert plain text lightweight markup emails to multipart/alterntive html emails')

    for settingKey in settings:
        setting = settings[settingKey]

        if setting.cli == True:
            longName  = '--' + setting.longName
            shortName = '-'  + setting.shortName

            # Notice that we do NOT specify the default value of the setting (see
            # above) as the default value for the argument. We use None instead,
            # and we DON'T use None for any of the default values for the settings.
            # This is so we can test whether the argument was specified on the
            # commandline. If it wasn't, it's value will be None, but if it was,
            # then it will have a value, even if that value happens to mathc the
            # default.
            # This is so that cli args - even if their values happen to match the
            # defaults - can overule config file values (which cause probelsm
            # because they have to be parses AFTER the commandline, because the
            # config file might be specified as an arg)
            parser.add_argument(longName, shortName, default=None)

    return parser

# get the filepath of the config file, if any
def getConfigFilePath():

    configFilePath = ''

    configFileName = 'multimarkmakerrc.toml'

    if os.getenv('MULTI_MARK_CONFIG_DIR'):
        mmmDirFilePath = '/'.join([os.getenv('MULTI_MARK_CONFIG_DIR'), configFileName])
        if os.path.exists(mmmDirFilePath):
            configFilePath = mmmDirFilePath + configFileName
    elif os.getenv('XDG_CONFIG_HOME'):
        xdgDirFilePath = '/'.join([os.getenv('XDG_CONFIG_HOME'), configFileName])
        if os.path.exists(xdgDirFilePath):
            configFilePath = xdgDirFilePath + configFileName
        elif os.path.exists(os.path.expandvars('~/.config')):
            configdirFilePath = '/'.join([os.path.expandvars('~/.config'), 'multi-mark-maker', configFileName])
            if os.path.exists(configdirFilePath):
                configFilePath = configdirFilePath + configFileName
                
    # return filepath of config file if it exists, '' otherwise
    return configFilePath

# Returns a copy of the slave dictionary, such that:
# - any key ALSO present in the master dictionary has it's value replaced by
#   the master value
# - any key / value present in the master but not the slave is inserted into
#   the slave
def mergeDown(slave, master):
    for key in master:
        slave.update({ key : master[key] })
    return slave

# Returns a copy of the slave dictionary, such that:
# - any key ALSO present in the master dictionary is ignored
# - any key / value present in the master but not the slave is inserted into
#   the slave
def mergeUp(slave, master):
    for key in master:
        if key not in slave:
            slave.update({ key : master[key] })
    return slave

def parseAdocSettings(options):

    adocOptions = {}

    for key in options:
        val = options[key]

        # require can be a list, or a string
        # either way, a LIST of requires is the adocOptions entry
        if key == 'require':
            if type(val) == str:
                val = [val]
            adocOptions.update({ key : val })

        # template-dir can be a list, or a string
        # either way, a LIST of template-dirs is the adocOptions entry
        elif key == 'template-dir':
            if type(val) == str:
                val = [val]
            adocOptions.update({ key : val })

        # add a dictionary 'attribute' to the adoc options, in which each key
        # is an attribute name and each value the corresponding value
        elif key == 'attribute':
            adocOptions.update( { key : {} } )
            for attribute in val: # val is the dictionary of attribute
                adocOptions[key].update( { attribute : val[attribute] } )

        # otherwise, just add { key : val } to the dictionary
        else:
            adocOptions[key] = val 

    return adocOptions            


# data is the dictionary from a toml config file
def parseCfg(data):

    cfgSettings = {}

    for key in data:
        val = data[key]

        # ascidoctor setings
        if key == 'asciidoctor-options':
            adocSettings = parseAdocSettings(val)
            setting = Setting(longName=key, value=adocSettings)
            cfgSettings.update( { key : setting } )

        # otherwise, if key is the name of a setting the settings, add 'key': 'value' to
        # the settings (ignore everything else)
        elif key != 'include':
            # this works, but there might be better ways...
            settingNames = declareSettings().keys()
            if key in settingNames:
                setting = Setting(longName=key, value=val)
                cfgSettings.update( { key : setting } )

        # IGNORE INCLUDES!!
        # (at the moment)

        # (include needs to come last, because we need to compare the current original and included values)
        # including other config files (recursively!, giving precedence to
        # closer files (i.e. this file overrules an included file)). This should
        # deal woith the possibility of lists of included files
        #elif key == 'include':
        #    #include can be a string or a list

        #    # STRING (top level) - then that file is included
        #    if type(val) == str:
        #        incData = toml.load(val)
        #        incSettings = parseCfg(incData)
        #    # LIST OF STRINGS (top level) - then each of those files is include
        #    # earlier-specified take precedence over later specified
        #    # (which is arbitrary and could be changeed if there was a good reason)
        #    elif type(val) == list:
        #        incSettings = {}
        #        for path in val:
        #            incData = toml.load(path)
        #            pathIncSettings = parseCfg(incData)
        #            incSettings = mergeUp(incSettings, pathIncSettings)

        #    # NOTE mergeup is not good enough here, because the included files
        #    # might have elements which hav ethe same key but different values
        #    # to those in the first file, AND which shouldn't just replace
        #    # those in the first file. (e.g. two different adoc options
        #    # dictionaries). I might need a recursive merginf function
        #    # specifically for this.
        #    # (for now, just don't use this feature)
        #    cfgSettings = mergeUp(cfgSettings, incSettings)

    return cfgSettings
    
# merge two dictionaries, such that:
# - the master takes precedence for key / value pairs with simple values
#   (strings, numbers, etc., not lists or dicts)
# - keys in slave but not master are ignored
# - complex values (lists, dicts etc.) will ve processed similarly, and
#   merged into the master version
# NOTE (could a variant use of this replace mergeUp / mergeDown?)
# NOTE (could I use an optional 'disallowed' to do some of the args cleaning HERE?)
def mergeSettings(master, slave):
    for key in slave:

        # all settings in master with value None, overwrite with slave setting.
        # all settings in slave but not master are copied over

        if (key in master and master[key].value == None) or (key not in master):
            setting = slave[key]
            val = setting.value
            vt = type(val)

            if vt != list and vt != dict:
                master.update( { key : setting } )

            # redo these two...
            elif vt == dict:
                newSetting = setting
                if key in master:
                    newSetting.value = mergeUp(master[key].value, val)
                master.update( { key : newSetting } )
            # merge slave and master lists into the master value
            elif vt == list:
                if key not in master:
                    newList = val
                else: 
                    newList = OrderedDict.fromkeys(master[key].value, val).keys()
                master.update( { key : newList } )

    return master

def getConfigFromFile(filepath):
    rawData = toml.load(filepath)

    data = {}
    
    settingsDict = declareSettings()
    for key in rawData:
        for settingKey in settingsDict:
            setting = settingsDict[settingKey]
            if setting.longName == key and setting.confFile == True:
                newKey = settingKey
                # data.update( { newKey : rawData[key] } )
                data[newKey] = rawData[key]

    return data

def getMessage(infile):
    # stdin
    if infile == '-':
        message = email.message_from_file(sys.stdin, policy=default)
    # not stdin
    else:
        with open(os.path.expandvars(infile)) as f:
            message = email.message_from_file(f, policy=default)

    return message

def settingsFromStrings(dct):

    settingsDict = {}
    
    for key in dct:
        setting = Setting(longName=key, value=dct[key])
        settingsDict.update( { key : setting } )

    return settingsDict

def convert(cmd, text):
    pipe = Popen(cmd, stdout=PIPE, stdin=PIPE)
    body = pipe.communicate(input=text)[0]
    return body

def getAdocString(optsDict):

    optsList = []

    for key in optsDict:
        if isAllowedAdoc[key] == True:
            val = optsDict[key]
            if key == 'attribute':
                for attr in val: # val will be a dict
                    if type(val[attr]) == str:
                        subOptStr = '--' + key + '=' + attr + '=' + val[attr]
                    elif val[attr] == True:
                        subOptStr = '--' + key + '=' + attr
                    elif val[attr] == False:
                        subOptStr = '--' + key + '=' + attr + '!'
                    optsList.append(subOptStr)
            elif key == 'template-dir':
                if type(val) == str:
                    optStr = '--' + key + ' ' + val
                else:
                    subOptsList = []
                    for tmp in val:
                        subOptStr = '--' + key + ' ' + tmp
                        subOptsList.append(subOptStr)
                        optsList.append(subOptStr)
            elif key == 'require':
                if type(val) == str:
                    optStr = '--' + key + ' ' + val
                else:
                    subOptsList = []
                    for req in val:
                        subOptStr = '--' + key + ' ' + req
                        subOptsList.append(subOptStr)
                        optsList.append(subOptStr)
            else:
                if val == True:
                    optStr = '--' + key
                elif type(val) != bool:
                    optStr = '--' + key + ' ' + val
                optsList.append(optStr)

    return optsList

def makePlainBody(inBody, settings):

    informat = settings['in_format'].value
    outformat = settings['out_format'].value

    # same formats
    if informat == outformat:
       return inBody

    # asciidoctor
    if informat == 'asciidoctor':
        adocSettings = getAdocString(settings['asciidoctor_options'].value)
        adocOpsString = shlex.split(settings['asciidoctor_options_string'].value)
        adocCmd = ['asciidoctor', '-b', 'docbook', '-o', '-', '-'] + adocSettings + adocOpsString
        pandocIn = convert(adocCmd, inBody)
        informat = 'docbook'
    else:
        pandocIn = inBody

    pandocCmd = ['pandoc', '-f', informat, '-t', outformat]
    plainBody = convert(pandocCmd, pandocIn)

    return plainBody

def makeHtmlBody(inBody, settings):
    
    informat = settings['in_format'].value

    if informat == 'asciidoctor':
        adocSettings = getAdocString(settings['asciidoctor_options'].value)
        adocOpsString = shlex.split(settings['asciidoctor_options_string'].value)
        cmd = ['asciidoctor', '-o', '-', '-'] + adocSettings + adocOpsString
    else:
        cmd = ['pandoc', '-f', informat, '-t', 'html']

    htmlBody = convert(cmd, inBody)

    return htmlBody

def makeMessageParts(inBody, settings):

    # correct encoding
    if isinstance(inBody, str):
        inBody = inBody.encode('utf-8')
    else:
        inBody = inBody.get_content(None, True)
        if not isinstance(inBody, bytes):
            inBody = inBody.encode('utf-8')

    # get the markdown and html parts
    plainBody = makePlainBody(inBody, settings).decode('utf-8')
    htmlBody  = makeHtmlBody(inBody, settings).decode('utf-8')

    return plainBody, htmlBody

def makeMultiMessage(inMessage, settings):

    # messages with attachments
    if inMessage.get_content_type() == 'multipart/mixed':
        inBody = (inMessage.get_body()).get_content()
        plainBody, htmlBody = makeMessageParts(inBody, settings)

        # make the multipart/alternative body
        altBody = MIMEPart()
        altBody.set_content(plainBody)
        altBody.add_alternative(htmlBody, subtype='html')
        
        outMessage = EmailMessage(policy=default)    

        # copy the header over to the new (out) message
        for field in inMessage.keys():
            outMessage[field] = inMessage[field]

        # make the first part of the outgoing message the multipart/alternative
        outMessage.attach(altBody)

        # attach all the attachments
        for attachment in inMessage.iter_attachments():
            outMessage.attach(attachment)

    # other messages
    else:
        inBody = inMessage.get_content()
        plainBody, htmlBody = makeMessageParts(inBody, settings)
        outMessage = inMessage # get an EmailMessage with the right header quickly
        outMessage.set_content(plainBody)
        outMessage.add_alternative(htmlBody, subtype='html')
    
    return outMessage

def writeMessage(message, outfile):

    if outfile == '-':
        print(message)

    else:
        fp = os.path.expandvars(outfile)
        f = open(fp, 'w')
        f.write(message.as_string())

def main():

    settings = declareSettings()

    # parse the comandline arguments
    cliParser = makeParser(settings)
    cliArgs = settingsFromStrings(vars(cliParser.parse_args()))

    # (config file has to come after cli args, because there may be a config
    # file specified in the cli args)

    # get config file IF it was not specified on the commandline
    if cliArgs['config_file'].value == None:
       settings['config_file'].value = getConfigFilePath()
    else: # otherwise set the config file as the one specified on the cli
       settings['config_file'].value = cliArgs['config_file'].value

    # if there's a config file, parse it.
    if settings['config_file'].value != '':
        data = getConfigFromFile(settings['config_file'].value)
        cfgFileSettings = parseCfg(data)
    # convenience, makes the merging functoin below simpler to implement
    else:
        cfgFileSettings = {}

    # make 'newSetting', by merging the cliargs and cfgFileSettings,
    # with precednece for cli args.
    newSettings = mergeSettings(cliArgs, cfgFileSettings)

    # merge newSettings into (master) settings
    settings = mergeSettings(newSettings, settings)

    # get the message form the relevant place
    message = getMessage(settings['infile'].value)

    outMessage = makeMultiMessage(message, settings)
        
    # write the message!!
    writeMessage(outMessage, settings['outfile'].value)

main()
