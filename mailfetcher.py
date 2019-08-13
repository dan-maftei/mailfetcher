#!/usr/bin/env python
#
# Copyright (c) 2019 Dan Maftei <dan.maftei@gmail.com>
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED
# TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS
# BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#

"""
A. MailFetcher does the following, in order:
      1. parse mailbox messages from WeTransfer 
      2. extract links to files sent via WeTransfer
      3. download files in a predefined folder
      4. unzip archives in place (if requested)
      5. delete extracted archives (if requested)


B. Requires python >= 3.6 and the following packages:
      requests
      bs4 (BeautifulSoup)
      transferwee (https://github.com/iamelot/transferwee


C. Usage in a python script:
      +-------------------------------------------+
      |from mailfetcher import MailFetcher        |
      |                                           |
      |worker = MailFetcher({                     |
      |      'server': 'mail.example.com',        |
      |      'user': 'john.doe',                  |
      |      'pass': 'SuperStr0ngPass',           |
      |      'outdir': '/store/zipfiles/'         |
      |  })                                       |
      | worker.fetch()                            |
      | worker.disconnect()                       |
      +-------------------------------------------+

"""


import os
import imaplib
import email
import shutil
import datetime
import zipfile

import transferwee
import bs4

defaults = {
    'mailbox': 'inbox',
    'autostart': False,
    'unzip': True,
    'keep_archive': True,
    'outdir': '/tmp/zipfiles'
}

class MailFetcher(object):
    
    """ Config from arguments """
    def __init__(self, config=None):
        self.config = defaults
        self.config.update(config)

        self.mailbox = None
        self.is_connected = self.connect()
        if self.config.get('autostart'):
            self.fetch()            

    def connect(self):
        """ Connect to IMAP and log in """
        server = self.config.get('server', None)
        username = self.config.get('user', None)
        password = self.config.get('pass', None)
        if server is None:
            return False

        self.mailbox = imaplib.IMAP4_SSL(server)
        if username is None or password is None:
            return False
        try:
            self.ts()
            print("Conectare la server...", end="")
            rv, data = self.mailbox.login(username, password)
        except imaplib.IMAP4.error as e:
            print("Failed: " + str(e))
            return False
        print("OK")
        return True

    def fetch(self):
        """ Fetch unread messages """
        if not self.is_connected:
            print("Error, not connected to IMAP server!")
            return None
        self.mailbox.select(self.config.get('mailbox'))
        tmp, data = self.mailbox.search(None, '(UNSEEN)')
        for num in data[0].split():
            tmp, data = self.mailbox.fetch(num, '(RFC822)')
            msg = email.message_from_bytes(data[0][1])
            links = self.get_wetransfer_links(msg)
            self.download_archives(links)

    def download_archives(self, links):
        # Download a list of files from the corresponding links
        os.makedirs(self.config.get('outdir'), exist_ok=True)
        os.chdir(self.config.get('outdir'))
        self.ts()
        print("Am gasit {} legaturi de download:".format(len(links)))
        for link in links:
            if "https://wetransfer.com/downloads" in link:
                self.log("Descarc de la {}.".format(link))
                file_name = transferwee.download(link)
                full_path = os.path.join(self.config.get('outdir'), file_name)
                if os.path.isfile(full_path):
                    size = os.path.getsize(full_path)
                    self.ts()
                    print("{:.<50s}{:5.1f} MB".format(file_name, size / 1024 / 1024))
                    if self.config.get('unzip'):
                        self.unzip_archive(file_name)

    def unzip_archive(self, file_name):
        # Unzip archive in 'outdir':
        with zipfile.ZipFile(file_name, 'r') as zipf:
            zipf.extractall(self.config.get('outdir'))
            self.log("{} extracted.".format(file_name))
            if not self.config.get('keep_archive'):
                os.unlink(file_name)
                self.log("{} deleted.".format(file_name))
            

    def get_wetransfer_links(self, msg):
        # Parse WeTransfer message and extract download link(s)
        # argument msg = message to be parsed
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                ctype = part.get_content_type()
                cdispo = str(part.get('Content-Disposition'))
                # skip any text/plain (txt) attachments
                if ctype == 'text/html' and 'attachment' not in cdispo:
                    body = part.get_payload(decode=True)  # decode
                    break
        else:
            body = msg.get_payload(decode=True)

        # Parse body
        links = set()
        soup =  bs4.BeautifulSoup(body, 'html.parser')
        for link in soup.find_all('span', class_="download_link_link"):
            links.add(link.text)
        for link in soup.find_all('a', class_="download_link_link", href=True):
            links.add(link['href'])

        return list(links)


    def ts(self):
        # Timestamp output
        print("[{:%Y-%m-%d %H:%M:%S}] ".format(datetime.datetime.now()), end="")


    def log(self, msg):
        # Log a message with timestamp
        self.ts()
        print(msg)


    def disconnect(self):
        # Disconnect from mailserver
        if self.is_connected:            
            self.mailbox.close()
            self.log("Deconectat de la serverul de IMAP.")


