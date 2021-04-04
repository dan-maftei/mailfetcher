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

    *** It is ASSUMED that the IMAP server uses SSL ***

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
import urllib
import imaplib
import email
import datetime
import zipfile

import transferwee
import bs4

# Default configuation
defaults = {
    'mailbox': 'inbox',
    'autostart': False,
    'unzip': True,
    'keep_archive': True,
    'outdir': '/tmp/zipfiles'
}


def _unquoted_filename(we_url):
    """ 
    Retrieve filename from WeTransfer link 
    (code duplicates the private function from 
    transferwee)
    """
    url = transferwee.download_url(we_url)
    name = urllib.parse.urlparse(url).path.split('/')[-1]
    return urllib.parse.unquote(name).replace('../', '').replace('/', '').replace('\\', '')


class MailFetcher(object):

    def __init__(self, config=None):
        """
        Config from default dictionary, then update from arguments

        :param dict config: configuration options
        """
        self.config = defaults
        self.config.update(config)

        self.is_connected = self.connect()

        if self.config.get('autostart', False):
            self.fetch()


    def connect(self):
        """
        Connect to IMAP and log in

        :return: True/False
        """
        server = self.config.get('server', None)
        username = self.config.get('user', None)
        password = self.config.get('pass', None)

        if server is None or username is None or password is None:
            return False

        self.mailbox = imaplib.IMAP4_SSL(server)
        if username is None or password is None:
            return False

        try:
            result, data = self.mailbox.login(username, password)
            self._log(f"Logged in on {server} as {username}.")
        except imaplib.IMAP4.error as e:
            self._log(f"Login failed: {e}.")
            return False

        return True


    def get_wetransfer_links(self, message):
        """
        Parse WeTransfer message and extract download link(s)

        :param message: message to be parsed, returned by email.message_from_bytes()
        :return: links found in message's body
        :rtype: list
        """
        if message.is_multipart():
            for part in message.walk():
                content_type = part.get_content_type()
                if content_type == 'text/html':
                    body = part.get_payload(decode=True)
                    break
        else:
            body = message.get_payload(decode=True)

        if body is None:
            self._log("Unable to parse message!")
            return []

        # Parse body using BeautifulSoup to search download links
        # Uses a set(), as download links may be found several
        # times in message body
        links = set()
        soup =  bs4.BeautifulSoup(body, 'html.parser')
        for link in soup.find_all('span', class_="download_link_link"):
            links.add(link.text)
        for link in soup.find_all('a', class_="download_link_link", href=True):
            links.add(link['href'])

        self._log("Found {} links to download.".format(len(links)))
        return list(links)

    def download_archives(self, links):
        """
        Download a list of files from the corresponding links

        :param list links: list of download links
        """

        # Create outdir and chdir to it
        os.makedirs(self.config.get('outdir'), exist_ok=True)
        os.chdir(self.config.get('outdir'))

        for link in links:
            if "wetransfer.com/downloads" in link:
                file_name = _unquoted_filename(link)
                self._log(f"Downloading {file_name}.")
                
                transferwee.download(link)
                
                full_path = os.path.join(self.config.get('outdir'), file_name)
                if os.path.isfile(full_path):
                    size = os.path.getsize(full_path)
                    print(f"{file_name:.<50s}{size/1024/1024:5.1f} MB")
                    if self.config.get('unzip'):
                        self.unzip_archive(file_name)
                else:
                    print("Failed!")


    def unzip_archive(self, file_name):
        """
        Extract an archive in 'outdir'

        :param file_name: archive file_name (full/relative path)

        """
        with zipfile.ZipFile(file_name, 'r') as zipf:
            zipf.extractall(self.config.get('outdir'))
            self._log("{} extracted.".format(file_name))

            # Delete source archive if configured so
            if not self.config.get('keep_archive'):
                try:
                    os.unlink(file_name)
                    self._log("{} deleted.".format(file_name))
                except Exception as e:
                    self._log("Unable to delete {}: {}.".format(file_name, str(e)))


    def fetch(self):
        """
        Fetch unread messages, parse email body for
        download links and download archives
        """
        if not self.is_connected:
            print("Error, not connected to IMAP server!")
            return None

        self.mailbox.select(self.config.get('mailbox'))

        # Search only unread messages
        result, data = self.mailbox.search(None, '(UNSEEN)')

        # Iterate over email found
        for mailID in data[0].split():
            result, data = self.mailbox.fetch(mailID, '(RFC822)')
            message = email.message_from_bytes(data[0][1])
            links = self.get_wetransfer_links(message)
            self.download_archives(links)


    def disconnect(self):
        """ Disconnect from mailserver """
        if self.is_connected:
            self.mailbox.close()
            self._log("Disconnected from {}.".format(self.config.get('server', 'IMAP server')))

    # Private utility methods
    def _ts(self):
        """ Timestamp output """
        print("[{:%Y-%m-%d %H:%M:%S}] ".format(datetime.datetime.now()), end="")


    def _log(self, msg):
        """ Log a message with timestamp """
        self._ts()
        print(msg)

