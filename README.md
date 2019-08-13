# mailfetcher

mailfetcher is a Python 3 wrapper against [transferwee](https://github.com/iamleot/transferwee)
to download (and optionally extract) zip archives received via [wetransfer](https://wetransfer.com). 
Download links for the files being received are extracted from the e-mail messages received upon transfer

## Usage

The entire code is wrapped in a class that is instantiated by passing various options as argument in a dictionary:

```python
from mailfetcher import MailFetcher 
worker = MailFetcher({            
    'server': 'mail.example.com',
    'user': 'john.doe',         
    'pass': 'SuperStr0ngPass', 
    'outdir': '/store/zipfiles/'
})                              
worker.fetch()                 
worker.disconnect()           
```

## Config options

| Key            | Default value          | Meaning                                                                             |
|----------------|------------------------|-------------------------------------------------------------------------------------|
| `server`       | None, write down yours | IMAP server address (hostname or IP number). Should use SSL (port 993)                                         |
| `user`         | None, write down yours | IMAP account username                                                               |
| `pass`         | None, write down yours | IMAP account password                                                               |
| `mailbox`      | `'inbox'`              | IMAP folder to search for UNREAD messages                                           |
| `outdir`       | `'/tmp/zipfiles'`      | Output folder (will download and extract archives here)                             |
| `autostart`    | `False`      | Start fetching after instantiation, no need to call `MailFetcher.fetch()` |
| `unzip`        | `True`       | Extract (unzip) automatically after download                                        |
| `keep_archive` | `True`       | Keep the zip after extracting, delete otherwise                                     |


